from jsonpath_ng.ext import parse

CLOUD_PARSER = {
    "openstack": {
        "instances": parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.id"
        ),
        "cores": parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.vcpus"
        ),
        "ram": parse(
            "resources[?type=openstack_compute_flavor_v2].instances[*].attributes.ram"
        ),
        "volumes": parse(
            "resources[?type=openstack_blockstorage_volume_v3].instances[*].attributes.size"
        ),
        "instance_volumes": parse(
            "resources[?type=openstack_compute_instance_v2].instances[*].attributes.block_device[*].volume_size"
        ),
        "public_ips": parse(
            "resources[?type=openstack_compute_floatingip_associate_v2].instances[*].attributes.id"
        ),
        "ports": parse(
            "resources[?type=openstack_networking_port_v2].instances[*].attributes.id"
        ),
        "security_groups": parse(
            "resources[?type=openstack_compute_secgroup_v2].instances[*].attributes.id"
        ),
    }
}

IMAGE_PARSER = parse("resources[?name=image].instances[0].attributes.name")
FREEIPA_PASSWD_PARSER = parse(
    "resources[?name=freeipa_passwd].instances[0].attributes.result"
)


class TerraformState:
    """
    TerraformState holds the state file of a cluster, i.e. the terraform.tfstate file.
    """

    __slots__ = [
        "instance_count",
        "cores",
        "ram",
        "volume_count",
        "volume_size",
        "image",
        "public_ip",
        "freeipa_passwd",
    ]

    def __init__(self, tf_state: object, cloud="openstack"):
        parser = CLOUD_PARSER[cloud]
        self.instance_count = len(parser["instances"].find(tf_state))
        self.cores = sum([cores.value for cores in parser["cores"].find(tf_state)])
        self.ram = sum([ram.value for ram in parser["ram"].find(tf_state)])

        volumes = parser["volumes"].find(tf_state)
        inst_volumes = parser["instance_volumes"].find(tf_state)
        self.volume_count = len(volumes) + len(inst_volumes)
        self.volume_size = sum(vol.value for vol in volumes) + sum(
            vol.value for vol in inst_volumes
        )

        self.public_ip = len(parser["public_ips"].find(tf_state))
        self.ports = len(parser["ports"].find(tf_state))
        self.security_groups = len(parser["security_groups"].find(tf_state))

        try:
            self.image = IMAGE_PARSER.find(tf_state)[0].value
        except:
            self.image = ""
        try:
            self.freeipa_passwd = FREEIPA_PASSWD_PARSER.find(tf_state)[0].value
        except:
            self.freeipa_passwd = None
