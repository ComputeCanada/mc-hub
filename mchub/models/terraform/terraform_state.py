from jsonpath_ng.ext import parse

CLOUD_PARSER = {
    "openstack": {
        "instance_count": parse(
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
        "freeipa_passwd",
        "resource_ids",
    ]

    def __init__(self, tf_state: dict, cloud="openstack"):
        self.resource_ids = {"instances": [], "volumes": [], "addresses": []}
        if cloud == "aws":
            self.instance_count = self.cores = self.ram = self.volume_count = self.volume_size = 0
            self.image = ""
            self.freeipa_passwd = None
            for resource in tf_state.get("resources", []):
                if resource.get("mode") == "data":
                    continue
                for instance in resource.get("instances", []):
                    attrs = instance.get("attributes", {})
                    kind = resource.get("type")
                    if kind == "aws_instance":
                        self.resource_ids["instances"].append(attrs["id"])
                        self.image = attrs.get("ami", "")
                        for block in attrs.get("root_block_device", []) + attrs.get("ebs_block_device", []):
                            if block.get("volume_id"):
                                self.resource_ids["volumes"].append(block["volume_id"])
                    elif kind == "aws_ebs_volume":
                        self.resource_ids["volumes"].append(attrs["id"])
                    elif kind == "aws_eip":
                        self.resource_ids["addresses"].append(attrs.get("allocation_id") or attrs["id"])
                    elif resource.get("name") == "freeipa_passwd":
                        self.freeipa_passwd = attrs.get("result")
            self.resource_ids = {k: list(set(v)) for k, v in self.resource_ids.items()}
            self.instance_count = len(self.resource_ids["instances"])
            return
        parser = CLOUD_PARSER[cloud]
        self.instance_count = len(parser["instance_count"].find(tf_state))
        self.cores = sum([cores.value for cores in parser["cores"].find(tf_state)])
        self.ram = sum([ram.value for ram in parser["ram"].find(tf_state)])

        volumes = parser["volumes"].find(tf_state)
        inst_volumes = parser["instance_volumes"].find(tf_state)
        self.volume_count = len(volumes) + len(inst_volumes)
        self.volume_size = sum(vol.value for vol in volumes) + sum(
            vol.value for vol in inst_volumes
        )

        try:
            self.image = IMAGE_PARSER.find(tf_state)[0].value
        except:
            self.image = ""
        try:
            self.freeipa_passwd = FREEIPA_PASSWD_PARSER.find(tf_state)[0].value
        except:
            self.freeipa_passwd = None
