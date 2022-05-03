import openstack

from os import environ, path
from re import search, IGNORECASE

CENTOS_VALID_IMAGES = r"centos"
OTHER_VALID_IMAGES = r"almalinux|rocky"

# Magic Castle requires 10 GB on the root disk for each node.
# Otherwise, it creates and mounts an external volume of 10 GB.
MINIMUM_ROOT_DISK_SIZE = 10

# Magic Castle requires the following specs for each instance category
INSTANCE_MINIMUM_REQUIREMENTS = {
    "mgmt": {
        "ram": 6144,
        "vcpus": 2
    },
    "login": {
        "ram": 2048,
        "vcpus": 2
    },
    "node": {
        "ram": 2048,
        "vcpus": 1
    },
}

def validate_flavor(category, flavor):
    return (
        flavor.vcpus >= INSTANCE_MINIMUM_REQUIREMENTS[category]["vcpus"] and
        flavor.ram   >= INSTANCE_MINIMUM_REQUIREMENTS[category]["ram"]
    )

class OpenStackManager:
    """
    OpenStackManager is responsible for fetching available OpenStack resources (instances, floating IPs, images,
    storage types) and usage quotas from the OpenStack API.
    """

    def __init__(
        self,
        cloud_id,
        *,
        pre_allocated_instance_count=0,
        pre_allocated_cores=0,
        pre_allocated_ram=0,
        pre_allocated_volume_count=0,
        pre_allocated_volume_size=0,
    ):
        self.connection = openstack.connect(cloud=cloud_id)
        self.project_id = self.connection.current_project_id

        self.__pre_allocated_instance_count = pre_allocated_instance_count
        self.__pre_allocated_cores = pre_allocated_cores
        self.__pre_allocated_ram = pre_allocated_ram
        self.__pre_allocated_volume_count = pre_allocated_volume_count
        self.__pre_allocated_volume_size = pre_allocated_volume_size

        self._volume_quotas = None
        self._compute_quotas = None
        self._network_quotas = None

        self._available_flavors = None

    @property
    def available_resources(self):
        return {
            "quotas": self.quotas,
            "resource_details": self.resource_details,
            "possible_resources": self.possible_resources,
        }

    @property
    def quotas(self):
        return {
            "instance_count": {"max": self.available_instance_count},
            "ram": {"max": self.available_ram},
            "vcpus": {"max": self.available_vcpus},
            "volume_count": {"max": self.available_volume_count},
            "volume_size": {"max": self.available_volume_size},
            "ips": {"max": self.available_floating_ip_count},
        }

    @property
    def possible_resources(self):
        return {
            "image": self.images,
            "instances": {
                tag: {
                    "type": [
                        flavor.name for flavor in self.available_flavors if validate_flavor(tag, flavor)
                    ],
                }
                for tag in INSTANCE_MINIMUM_REQUIREMENTS
            },
            "volumes": {},
        }

    @property
    def resource_details(self):
        return {
            "instance_types": [
                {
                    "name": flavor.name,
                    "vcpus": flavor.vcpus,
                    "ram": flavor.ram,
                    "required_volume_count": 1
                    if flavor.disk < MINIMUM_ROOT_DISK_SIZE
                    else 0,
                    "required_volume_size": MINIMUM_ROOT_DISK_SIZE
                    if flavor.disk < MINIMUM_ROOT_DISK_SIZE
                    else 0,
                }
                for flavor in self.available_flavors
            ]
        }

    @property
    def images(self):
        centos = []
        others = []
        for image in self.connection.image.images():
            if search(CENTOS_VALID_IMAGES, image.name, IGNORECASE):
                centos.append(image.name)
            elif search(OTHER_VALID_IMAGES, image.name, IGNORECASE):
                others.append(image.name)
        centos.sort()
        others.sort()
        return centos + others

    @property
    def available_flavors(self):
        if self._available_flavors is None:
            self._available_flavors = list(self.connection.compute.flavors())
            self._available_flavors.sort(key=lambda flavor: (flavor.ram, flavor.vcpus))
        return self._available_flavors

    @property
    def available_tags(self):
        tags = {
            "mgmt": ["mgmt", "nfs", "puppet"],
            "login": ["login", "proxy", "public"],
            "node": ["node"],
        }
        return tags

    @property
    def available_instance_count(self):
        return (
            self.__pre_allocated_instance_count
            + self.compute_quotas["instances"]["limit"]
            - self.compute_quotas["instances"]["in_use"]
        )

    @property
    def available_ram(self):
        return (
            self.__pre_allocated_ram
            + self.compute_quotas["ram"]["limit"]
            - self.compute_quotas["ram"]["in_use"]
        )

    @property
    def available_vcpus(self):
        return (
            self.__pre_allocated_cores
            + self.compute_quotas["cores"]["limit"]
            - self.compute_quotas["cores"]["in_use"]
        )

    @property
    def available_volume_count(self):
        return (
            self.__pre_allocated_volume_count
            + self.volume_quotas["volumes"]["limit"]
            - self.volume_quotas["volumes"]["in_use"]
        )

    @property
    def available_volume_size(self):
        return (
            self.__pre_allocated_volume_size
            + self.volume_quotas["gigabytes"]["limit"]
            - self.volume_quotas["gigabytes"]["in_use"]
        )

    @property
    def available_floating_ip_count(self):
        return (
            self.network_quotas["floatingip"]["limit"]
            - self.network_quotas["floatingip"]["used"]
        )

    @property
    def volume_quotas(self):
        if self._volume_quotas is None:
            # Normally, we should use self.__connection.get_volume_quotas(...) from openstack sdk.
            # However, this method executes the action
            # identity:list_projects from the identity api which is forbidden
            # to some users.
            #
            # API documentation:
            # https://docs.openstack.org/api-ref/block-storage/v3/index.html?expanded=show-quotas-for-a-project-detail#show-quotas-for-a-project
            self._volume_quotas = self.connection.block_storage.get(
                f"/os-quota-sets/{self.project_id}?usage=true"
            ).json()["quota_set"]
        return self._volume_quotas

    @property
    def compute_quotas(self):
        if self._compute_quotas is None:
            # Normally, we should use self.__connection.get_compute_quotas(...) from openstack sdk.
            # However, this method executes the action
            # identity:list_projects from the identity api which is forbidden
            # to some users.
            #
            # API documentation:
            # https://docs.openstack.org/api-ref/compute/?expanded=show-a-quota-detail#show-a-quota
            self._compute_quotas = self.connection.compute.get(
                f"/os-quota-sets/{self.project_id}/detail"
            ).json()["quota_set"]
        return self._compute_quotas

    @property
    def network_quotas(self):
        if self._network_quotas is None:
            # Normally, we should use self.__connection.get_network_quotas(...) from openstack sdk.
            # However, this method executes the action
            # identity:list_projects from the identity api which is forbidden
            # to some users.
            #
            # API documentation:
            # https://docs.openstack.org/api-ref/network/v2/?expanded=show-quota-details-for-a-tenant-detail#show-quota-details-for-a-tenant
            self._network_quotas = self.connection.network.get(
                f"/quotas/{self.project_id}/details.json"
            ).json()["quota"]
        return self._network_quotas
