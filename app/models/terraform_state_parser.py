from jsonpath_ng.ext import parse
from models.constants import INSTANCE_CATEGORIES, STORAGE_SPACES


def default(default_value):
    """
    This decorator allows a function that normally throws an exception to return a default value instead.
    :param default_value: The default return value, in case of an exception.
    :return: The decorated function's return value or the default value.
    """

    def decorator(function):
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception:
                return default_value

        return wrapper

    return decorator


class TerraformStateParser:
    """
    TerraformStateParser handles the parsing of the state file of a cluster, i.e. the terraform.tfstate file.
    It makes it easy to get access to the important variables in the state (intance types, guest password, ...)
    through the get_configuration method.
    """

    def __init__(self, tf_state: object):
        self.__tf_state = tf_state

    def get_configuration(self):
        return {
            "cluster_name": self.__get_cluster_name(),
            "domain": self.__get_domain(),
            "image": self.__get_image(),
            "nb_users": self.__get_nb_users(),
            "instances": self.__get_instances(),
            "storage": self.__get_storage(),
            "public_keys": self.__get_public_keys(),
            "guest_passwd": self.__get_guest_passwd(),
            "os_floating_ips": self.get_os_floating_ips(),
        }

    def get_instance_count(self) -> int:
        parser = parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.id"
        )
        return len(parser.find(self.__tf_state))

    def get_cores(self) -> int:
        parser = parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.vcpus"
        )
        return sum([cores.value for cores in parser.find(self.__tf_state)])

    def get_ram(self) -> int:
        parser = parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.ram"
        )
        return sum([ram.value for ram in parser.find(self.__tf_state)])

    def get_volume_count(self) -> int:
        """
        Calculates the number of volumes used by the cluster.
        This includes both the volumes associated with an instance
        and the external volumes (NFS).
        :return: The number of volumes in the cluster
        """
        root_storage_parser = parse(
            "resources[?type=openstack_compute_instance_v2].instances[*].attributes.block_device[*].volume_size"
        )
        external_storage_parser = parse(
            "resources[?type=openstack_blockstorage_volume_v2].instances[*].attributes.size"
        )
        return len(root_storage_parser.find(self.__tf_state)) + len(
            external_storage_parser.find(self.__tf_state)
        )

    def get_volume_size(self) -> int:
        """
        Calculates the amount of volume storage used by the cluster.
        This includes both the volumes associated with an instance
        and the external volumes (NFS).
        :return: The number of gibibytes used by all volumes in the cluster
        """
        root_storage_parser = parse(
            "resources[?type=openstack_compute_instance_v2].instances[*].attributes.block_device[*].volume_size"
        )
        external_storage_parser = parse(
            "resources[?type=openstack_blockstorage_volume_v2].instances[*].attributes.size"
        )
        return sum(
            [
                storage.value
                for storage in root_storage_parser.find(self.__tf_state)
                + external_storage_parser.find(self.__tf_state)
            ]
        )

    def get_os_floating_ips(self):
        parser = parse(
            "resources[?type=openstack_compute_floatingip_associate_v2].instances[*].attributes.floating_ip"
        )
        return [match.value for match in parser.find(self.__tf_state)]

    @default("")
    def __get_cluster_name(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.cluster_name"
        )
        return parser.find(self.__tf_state)[0].value

    @default("")
    def __get_domain(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.domain_name"
        )
        full_domain_name = parser.find(self.__tf_state)[0].value
        return full_domain_name[len(self.__get_cluster_name()) + 1 :]

    @default("")
    def __get_image(self):
        parser = parse("resources[?name=image].instances[0].attributes.name")
        return parser.find(self.__tf_state)[0].value

    @default(0)
    def __get_nb_users(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.nb_users"
        )
        return int(parser.find(self.__tf_state)[0].value)

    def __get_instances(self):
        @default("")
        def get_instance_type(instance_category):
            parser = parse(
                f'resources[?type="openstack_compute_instance_v2" & name="{instance_category}"].instances[0].attributes.flavor_name'
            )
            return parser.find(self.__tf_state)[0].value

        @default(0)
        def get_instance_count(instance_category):
            parser = parse(
                f'resources[?type="openstack_compute_instance_v2" & name="{instance_category}"].instances[*]'
            )
            return len(parser.find(self.__tf_state))

        return {
            instance_category: {
                "type": get_instance_type(instance_category),
                "count": get_instance_count(instance_category),
            }
            for instance_category in INSTANCE_CATEGORIES
        }

    def __get_storage(self):
        @default(0)
        def get_external_storage_size(space_name):
            parser = parse(
                f'resources[?type="openstack_blockstorage_volume_v2" & name="{space_name}"].instances[0].attributes.size'
            )
            return int(parser.find(self.__tf_state)[0].value)

        storage = {
            f"{space}_size": get_external_storage_size(space)
            for space in STORAGE_SPACES
        }
        storage["type"] = "nfs"
        return storage

    def __get_public_keys(self):
        parser = parse(
            "resources[?type=openstack_compute_keypair_v2].instances[*].attributes.public_key"
        )
        return [match.value for match in parser.find(self.__tf_state)]

    @default("")
    def __get_guest_passwd(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.guest_passwd"
        )
        return parser.find(self.__tf_state)[0].value
