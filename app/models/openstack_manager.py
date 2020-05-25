import openstack
from os import environ
from models.constants import INSTANCE_CATEGORIES


class OpenStackManager:
    def __init__(self):
        self.__connection = openstack.connect()

    def __get_images(self):
        return [image.name for image in self.__connection.image.images()]

    def __get_available_floating_ips(self):
        return [
            ip.floating_ip_address
            for ip in self.__connection.network.ips(status="DOWN")
        ]

    def __get_flavors(self):
        quotas = self.__get_compute_quotas()
        available_ram = quotas["ram"]["limit"] - quotas["ram"]["in_use"]
        available_cores = quotas["cores"]["limit"] - quotas["cores"]["in_use"]
        return [
            flavor.name
            for flavor in self.__connection.compute.flavors()
            if flavor.ram <= available_ram and flavor.vcpus <= available_cores
        ]

    def __get_compute_quotas(self):
        # Normally, we should use self.__connection.get_compute_quotas(...) from openstack sdk.
        # However, this method executes the action
        # identity:list_projects from the identity api which is forbidden
        # to some users.

        return self.__connection.compute.get(
            f"/os-quota-sets/{environ['OS_PROJECT_ID']}/detail"
        ).json()["quota_set"]

    def get_fields(self):
        flavors = self.__get_flavors()
        return {
            "image": self.__get_images(),
            "instances": {category: flavors for category in INSTANCE_CATEGORIES},
            "os_floating_ips": self.__get_available_floating_ips(),
            "compute_quotas": self.__get_compute_quotas(),
        }
