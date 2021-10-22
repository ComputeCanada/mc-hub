from os import environ, path
from models.constants import INSTANCE_CATEGORIES, AUTO_ALLOCATED_IP_LABEL
from re import search, IGNORECASE
import openstack

VALID_IMAGES = r"centos|almalinux|rocky"
OPENSTACK_CONFIG_FILENAME = "clouds.yaml"
OPENSTACK_CONFIG_PATH = path.join(
    environ["HOME"], ".config", "openstack", OPENSTACK_CONFIG_FILENAME
)

# Magic Castle requires 10 GB on the root disk for each node.
# Otherwise, it creates and mounts an external volume of 10 GB.
MINIMUM_ROOT_DISK_SIZE = 10

# Magic Castle requires the following specs for each instance category
INSTANCE_MINIMUM_REQUIREMENTS = {
    "mgmt": {"ram": 6144, "vcpus": 2},
    "login": {"ram": 2048, "vcpus": 2},
    "node": {"ram": 2048, "vcpus": 1},
}


class OpenStackManager:
    """
    OpenStackManager is responsible for fetching available OpenStack resources (instances, floating IPs, images,
    storage types) and usage quotas from the OpenStack API.
    """

    def __init__(
        self,
        *,
        pre_allocated_instance_count=0,
        pre_allocated_cores=0,
        pre_allocated_ram=0,
        pre_allocated_volume_count=0,
        pre_allocated_volume_size=0,
    ):
        self.__connection = openstack.connect()
        self.__project_id = self.__connection.current_project_id

        self.__pre_allocated_instance_count = pre_allocated_instance_count
        self.__pre_allocated_cores = pre_allocated_cores
        self.__pre_allocated_ram = pre_allocated_ram
        self.__pre_allocated_volume_count = pre_allocated_volume_count
        self.__pre_allocated_volume_size = pre_allocated_volume_size

        self.__volume_quotas = None
        self.__compute_quotas = None
        self.__network_quotas = None

        self.__available_flavors = None

    @staticmethod
    def test_connection():
        """
        Attempts to connect to the OpenStack API and raises an exception if the connection fails.
        """
        if not path.isfile(OPENSTACK_CONFIG_PATH):
            raise FileNotFoundError(f"The {OPENSTACK_CONFIG_FILENAME} was not found.")
        openstack.connect()

    def get_available_resources(self):
        return {
            "quotas": self.__get_quotas(),
            "resource_details": self.__get_resource_details(),
            "possible_resources": self.__get_possible_resources(),
        }

    def __get_quotas(self):
        return {
            "instance_count": {"max": self.__get_available_instance_count()},
            "ram": {"max": self.__get_available_ram()},
            "vcpus": {"max": self.__get_available_vcpus()},
            "volume_count": {"max": self.__get_available_volume_count()},
            "volume_size": {"max": self.__get_available_volume_size()},
        }

    def __get_possible_resources(self):
        return {
            "image": self.__get_images(),
            "instances": {
                category: {
                    "type": [
                        flavor.name for flavor in self.__get_available_flavors(category)
                    ],
                    "tags": self.__get_available_tags(category)
                }
                for category in INSTANCE_CATEGORIES
            },
            "volumes": { },
        }

    def __get_resource_details(self):
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
                for flavor in self.__get_available_flavors()
            ]
        }

    def __get_images(self):
        return [
            image.name
            for image in self.__connection.image.images()
            if search(VALID_IMAGES, image.name, IGNORECASE)
        ]

    def __get_available_flavors(self, category=None):
        if self.__available_flavors is None:
            self.__available_flavors = list(self.__connection.compute.flavors())
            self.__available_flavors.sort(key=lambda flavor: (flavor.ram, flavor.vcpus))

        def validate_flavor_requirements(flavor):
            return (
                flavor.vcpus >= INSTANCE_MINIMUM_REQUIREMENTS[category]["vcpus"]
                and flavor.ram >= INSTANCE_MINIMUM_REQUIREMENTS[category]["ram"]
            )

        if category is None:
            return self.__available_flavors
        else:
            return list(filter(validate_flavor_requirements, self.__available_flavors))

    def __get_available_tags(self, category=None):
        tags = {
            'mgmt' : ['mgmt', 'nfs', 'puppet'],
            'login' : ['login', 'proxy', 'public'],
            'node' : ['node'],
        }
        return tags[category]

    def __get_available_instance_count(self):
        return (
            self.__pre_allocated_instance_count
            + self.__get_compute_quotas()["instances"]["limit"]
            - self.__get_compute_quotas()["instances"]["in_use"]
        )

    def __get_available_ram(self):
        return (
            self.__pre_allocated_ram
            + self.__get_compute_quotas()["ram"]["limit"]
            - self.__get_compute_quotas()["ram"]["in_use"]
        )

    def __get_available_vcpus(self):
        return (
            self.__pre_allocated_cores
            + self.__get_compute_quotas()["cores"]["limit"]
            - self.__get_compute_quotas()["cores"]["in_use"]
        )

    def __get_available_volume_count(self):
        return (
            self.__pre_allocated_volume_count
            + self.__get_volume_quotas()["volumes"]["limit"]
            - self.__get_volume_quotas()["volumes"]["in_use"]
        )

    def __get_available_volume_size(self):
        return (
            self.__pre_allocated_volume_size
            + self.__get_volume_quotas()["gigabytes"]["limit"]
            - self.__get_volume_quotas()["gigabytes"]["in_use"]
        )

    def __get_non_allocated_floating_ip_count(self):
        return (
            self.__get_network_quotas()["floatingip"]["limit"]
            - self.__get_network_quotas()["floatingip"]["used"]
        )

    def __get_volume_quotas(self):
        if self.__volume_quotas is None:
            # Normally, we should use self.__connection.get_volume_quotas(...) from openstack sdk.
            # However, this method executes the action
            # identity:list_projects from the identity api which is forbidden
            # to some users.
            #
            # API documentation:
            # https://docs.openstack.org/api-ref/block-storage/v3/index.html?expanded=show-quotas-for-a-project-detail#show-quotas-for-a-project
            self.__volume_quotas = self.__connection.block_storage.get(
                f"/os-quota-sets/{self.__project_id}?usage=true"
            ).json()["quota_set"]
        return self.__volume_quotas

    def __get_compute_quotas(self):
        if self.__compute_quotas is None:
            # Normally, we should use self.__connection.get_compute_quotas(...) from openstack sdk.
            # However, this method executes the action
            # identity:list_projects from the identity api which is forbidden
            # to some users.
            #
            # API documentation:
            # https://docs.openstack.org/api-ref/compute/?expanded=show-a-quota-detail#show-a-quota
            self.__compute_quotas = self.__connection.compute.get(
                f"/os-quota-sets/{self.__project_id}/detail"
            ).json()["quota_set"]
        return self.__compute_quotas

    def __get_network_quotas(self):
        if self.__network_quotas is None:
            # Normally, we should use self.__connection.get_network_quotas(...) from openstack sdk.
            # However, this method executes the action
            # identity:list_projects from the identity api which is forbidden
            # to some users.
            #
            # API documentation:
            # https://docs.openstack.org/api-ref/network/v2/?expanded=show-quota-details-for-a-tenant-detail#show-quota-details-for-a-tenant
            self.__network_quotas = self.__connection.network.get(
                f"/quotas/{self.__project_id}/details.json"
            ).json()["quota"]
        return self.__network_quotas
