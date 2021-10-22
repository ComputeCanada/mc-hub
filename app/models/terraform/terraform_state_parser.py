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
    It makes it easy to get access to the important variables in the state (instance types, guest password, ...)
    through the get_configuration method.
    """

    def __init__(self, tf_state: object):
        self.tf_state = tf_state

    def get_partial_configuration(self):
        """
        Gets all the information required for a MagicCastleConfiguration object, except for the hieradata field,
        which is not available in the terraform state.

        :return: The dictionary containing the partial configuration.
        """
        return {
            "cluster_name": self.__get_cluster_name(),
            "domain": self.__get_domain(),
            "image": self.__get_image(),
            "instances": self.__get_instances(),
            "public_keys": self.__get_public_keys(),
        }

    def get_instance_count(self) -> int:
        parser = parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.id"
        )
        return len(parser.find(self.tf_state))

    def get_cores(self) -> int:
        parser = parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.vcpus"
        )
        return sum([cores.value for cores in parser.find(self.tf_state)])

    def get_ram(self) -> int:
        parser = parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.ram"
        )
        return sum([ram.value for ram in parser.find(self.tf_state)])

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
            "resources[?type=openstack_blockstorage_volume_v3].instances[*].attributes.size"
        )
        return len(root_storage_parser.find(self.tf_state)) + len(
            external_storage_parser.find(self.tf_state)
        )

    def get_volume_size(self) -> int:
        """
        Calculates the amount of volume storage used by the cluster.
        This includes both the volumes associated with an instance
        and the external volumes (NFS).

        :return: The number of gibibytes used by all volumes in the cluster
        """
        root_storage_parser = parse(
            'resources[?type="openstack_compute_instance_v2" & name="instances"].instances[*].attributes.block_device[*].volume_size'
        )
        external_storage_parser = parse(
            "resources[?type=openstack_blockstorage_volume_v3].instances[*].attributes.size"
        )
        return sum(
            [
                storage.value
                for storage in root_storage_parser.find(self.tf_state)
                + external_storage_parser.find(self.tf_state)
            ]
        )

    @default("")
    def __get_cluster_name(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.cluster_name"
        )
        return parser.find(self.tf_state)[0].value

    @default("")
    def __get_domain(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.domain_name"
        )
        full_domain_name = parser.find(self.tf_state)[0].value
        return full_domain_name[len(self.__get_cluster_name()) + 1 :]

    @default("")
    def __get_image(self):
        parser = parse("resources[?name=image].instances[0].attributes.name")
        return parser.find(self.tf_state)[0].value

    def __get_instances(self):
        @default("")
        def get_instance_type(instance_category):
            parser = parse(
                f'resources[?type="openstack_compute_instance_v2" & name="instances"].instances[?index_key="{instance_category}1"].attributes.flavor_name'
            )
            return parser.find(self.tf_state)[0].value

        @default(0)
        def get_instance_count(instance_category):
            parser = parse(
                f'resources[?type="openstack_compute_instance_v2" & name="instances"].instances[*].index_key'
            )
            return sum(key.value.startswith(instance_category) for key in parser.find(self.tf_state))

        return {
            instance_category: {
                "type": get_instance_type(instance_category),
                "count": get_instance_count(instance_category),
            }
            for instance_category in INSTANCE_CATEGORIES
        }

    def __get_public_keys(self):
        parser = parse(
            "resources[?type=openstack_compute_keypair_v2].instances[*].attributes.public_key"
        )
        public_keys = [match.value for match in parser.find(self.tf_state)]
        return public_keys

    @default(None)
    def get_freeipa_passwd(self):
        parser = parse(
            "resources[?name=freeipa_passwd].instances[0].attributes.result"
        )
        return parser.find(self.tf_state)[0].value
