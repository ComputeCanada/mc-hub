from jsonpath_ng.ext import parse

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
    def __get_image(self):
        parser = parse("resources[?name=image].instances[0].attributes.name")
        return parser.find(self.tf_state)[0].value

    @default(None)
    def get_freeipa_passwd(self):
        parser = parse(
            "resources[?name=freeipa_passwd].instances[0].attributes.result"
        )
        return parser.find(self.tf_state)[0].value
