import openstack

from functools import cache
from os import environ, path
from re import match, IGNORECASE, compile

VALID_IMAGES_REGEX_ARRAY = [
    compile(r"rocky-8", IGNORECASE),
    compile(r"almalinux-8", IGNORECASE),
    compile(r"centos-8", IGNORECASE),
]

# Magic Castle requires 10 GB on the root disk for each node.
# Otherwise, it creates and mounts an external volume of 10 GB.
MINIMUM_ROOT_DISK_SIZE = 10

# Magic Castle requires the following specs for each instance category
TAG_MINIMUM_REQUIREMENTS = {
    "mgmt": {"ram": 6144, "vcpus": 2},
    "login": {"ram": 2048, "vcpus": 2},
    "node": {"ram": 2048, "vcpus": 1},
}


def validate_flavor(tag, flavor):
    return (
        flavor.vcpus >= TAG_MINIMUM_REQUIREMENTS[tag]["vcpus"]
        and flavor.ram >= TAG_MINIMUM_REQUIREMENTS[tag]["ram"]
    )


class OpenStackManager:
    """
    OpenStackManager is responsible for fetching available OpenStack resources (instances, floating IPs, images,
    storage types) and usage quotas from the OpenStack API.
    """

    __slots__ = [
        "project",
        "allocated_resources",
    ]

    def __init__(
        self,
        project,
        allocated_resources,
    ):
        self.project = project
        self.allocated_resources = allocated_resources

    @property
    @cache
    def connection(self):
        # Convert OS_* environment variable in keyword arguments
        kargs = {key[3:].lower(): value for key, value in self.project.env.items()}
        kargs["auth_type"] = "v3applicationcredential"
        return openstack.connect(**kargs)

    @property
    @cache
    def project_id(self):
        return self.connection.current_project_id

    @property
    def env(self):
        return self.project.env

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
            "instance_count": self.available_instance_count,
            "ram": self.available_ram,
            "vcpus": self.available_vcpus,
            "volume_count": self.available_volume_count,
            "volume_size": self.available_volume_size,
            "ips": self.available_floating_ip,
            "ports": self.available_ports,
            "security_groups": self.available_security_groups,
        }

    @property
    def possible_resources(self):
        return {
            "image": self.images,
            "tag_types": {
                tag: [
                    flavor.name
                    for flavor in self.available_flavors
                    if validate_flavor(tag, flavor)
                ]
                for tag in TAG_MINIMUM_REQUIREMENTS
            },
            "types": [flavor.name for flavor in self.available_flavors],
            "volumes": [type.name for type in self.available_volume_types],
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
    @cache
    def images(self):
        images = []
        for image in self.connection.image.images():
            for idx, pattern in enumerate(VALID_IMAGES_REGEX_ARRAY):
                if pattern.match(image.name):
                    images.append((idx, image.name))
                    break
        images.sort()
        return [image[1] for image in images]

    @property
    @cache
    def available_flavors(self):
        available_flavors = list(self.connection.compute.flavors())
        available_flavors.sort(key=lambda flavor: (flavor.ram, flavor.vcpus))
        return available_flavors

    @property
    @cache
    def available_volume_types(self):
        return list(self.connection.block_storage.types())

    @property
    def available_instance_count(self):
        return (
            self.allocated_resources.get("instance_count", 0)
            + self.compute_quotas["instances"]["limit"]
            - self.compute_quotas["instances"]["in_use"]
        )

    @property
    def available_ram(self):
        return (
            self.allocated_resources.get("ram", 0)
            + self.compute_quotas["ram"]["limit"]
            - self.compute_quotas["ram"]["in_use"]
        )

    @property
    def available_vcpus(self):
        return (
            self.allocated_resources.get("cores", 0)
            + self.compute_quotas["cores"]["limit"]
            - self.compute_quotas["cores"]["in_use"]
        )

    @property
    def available_volume_count(self):
        return (
            self.allocated_resources.get("volumes", 0)
            + self.volume_quotas["volumes"]["limit"]
            - self.volume_quotas["volumes"]["in_use"]
        )

    @property
    def available_volume_size(self):
        return (
            self.allocated_resources.get("volume_size", 0)
            + self.volume_quotas["gigabytes"]["limit"]
            - self.volume_quotas["gigabytes"]["in_use"]
        )

    @property
    def available_floating_ip(self):
        return (
            self.allocated_resources.get("public_ip", 0)
            + self.network_quotas["floatingip"]["limit"]
            - self.network_quotas["floatingip"]["used"]
        )

    @property
    def available_ports(self):
        return (
            self.allocated_resources.get("ports", 0)
            + self.network_quotas["ports"]["limit"]
            - self.network_quotas["ports"]["used"]
        )

    @property
    def available_security_groups(self):
        return (
            self.allocated_resources.get("security_groups", 0)
            + self.network_quotas["security_groups"]["limit"]
            - self.network_quotas["security_groups"]["used"]
        )

    @property
    @cache
    def volume_quotas(self):
        # Normally, we should use self.__connection.get_volume_quotas(...) from openstack sdk.
        # However, this method executes the action
        # identity:list_projects from the identity api which is forbidden
        # to some users.
        #
        # API documentation:
        # https://docs.openstack.org/api-ref/block-storage/v3/index.html?expanded=show-quotas-for-a-project-detail#show-quotas-for-a-project
        return self.connection.block_storage.get(
            f"/os-quota-sets/{self.project_id}?usage=true"
        ).json()["quota_set"]

    @property
    @cache
    def compute_quotas(self):
        # Normally, we should use self.__connection.get_compute_quotas(...) from openstack sdk.
        # However, this method executes the action
        # identity:list_projects from the identity api which is forbidden
        # to some users.
        #
        # API documentation:
        # https://docs.openstack.org/api-ref/compute/?expanded=show-a-quota-detail#show-a-quota
        return self.connection.compute.get(
            f"/os-quota-sets/{self.project_id}/detail"
        ).json()["quota_set"]

    @property
    @cache
    def network_quotas(self):
        return self.connection.network.get_quota(self.project_id, details=True)
