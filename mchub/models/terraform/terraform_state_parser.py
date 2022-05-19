from jsonpath_ng.ext import parse


class TerraformStateParser:
    """
    TerraformStateParser handles the parsing of the state file of a cluster, i.e. the terraform.tfstate file.
    It makes it easy to get access to the important variables in the state (instance types, guest password, ...)
    through the get_configuration method.
    """

    INSTANCE_COUNT = "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.id"
    CORES = "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.vcpus"
    RAM = "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.ram"
    VOLUMES = "resources[?type=openstack_blockstorage_volume_v3].instances[*].attributes.size"
    INSTANCE_VOLUMES = "resources[?type=openstack_compute_instance_v2].instances[*].attributes.block_device[*].volume_size"
    IMAGE = "resources[?name=image].instances[0].attributes.name"
    FREEIPA_PASSWD = "resources[?name=freeipa_passwd].instances[0].attributes.result"

    def __init__(self, tf_state: object):
        self.tf_state = tf_state
        self.instance_count = len(parse(self.INSTANCE_COUNT).find(self.tf_state))
        self.cores = sum([cores.value for cores in parse(self.CORES).find(self.tf_state)])
        self.ram = sum([ram.value for ram in parse(self.RAM).find(self.tf_state)])

        volumes = parse(self.VOLUMES).find(self.tf_state)
        inst_volumes = parse(self.INSTANCE_VOLUMES).find(self.tf_state)
        self.volume_count = len(volumes) + len(inst_volumes)
        self.volume_size = sum(vol.value for vol in volumes) + sum(vol.value for vol in inst_volumes)

        try:
            self.image = parse(self.IMAGE).find(self.tf_state)[0].value
        except:
            self.image = ""
        try:
            self.freeipa_passwd = parse(self.FREEIPA_PASSWD).find(self.tf_state)[0].value
        except:
            self.freeipa_passwd = ""
