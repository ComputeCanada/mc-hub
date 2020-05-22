from jsonpath_ng.ext import parse
from models.constants import INSTANCE_CATEGORIES, STORAGE_SPACES


class TerraformStateParser:
    def __init__(self, tf_state: object):
        self.__tf_state = tf_state

    def __get_cluster_name(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.cluster_name"
        )
        return parser.find(self.__tf_state)[0].value

    def __get_domain(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.domain_name"
        )
        full_domain_name = parser.find(self.__tf_state)[0].value
        return full_domain_name[len(self.__get_cluster_name()) + 1 :]

    def __get_image(self):
        parser = parse("resources[?name=image].instances[0].attributes.name")
        return parser.find(self.__tf_state)[0].value

    def __get_nb_users(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.nb_users"
        )
        return int(parser.find(self.__tf_state)[0].value)

    def __get_instances(self):
        def get_instance_type(instance_category):
            parser = parse(
                f'resources[?type="openstack_compute_instance_v2" & name="{instance_category}"].instances[0].attributes.flavor_name'
            )
            return parser.find(self.__tf_state)[0].value

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
        def get_storage_size(space_name):
            parser = parse(
                f'resources[?type="openstack_blockstorage_volume_v2" & name="{space_name}"].instances[0].attributes.size'
            )
            return int(parser.find(self.__tf_state)[0].value)

        storage = {f"{space}_size": get_storage_size(space) for space in STORAGE_SPACES}
        storage["type"] = "nfs"
        return storage

    def __get_public_keys(self):
        parser = parse(
            "resources[?type=openstack_compute_keypair_v2].instances[*].attributes.public_key"
        )
        return [match.value for match in parser.find(self.__tf_state)]

    def __get_guest_passwd(self):
        parser = parse(
            "resources[?name=hieradata].instances[0].attributes.vars.guest_passwd"
        )
        return parser.find(self.__tf_state)[0].value

    def __get_os_floating_ips(self):
        parser = parse(
            "resources[?type=openstack_compute_floatingip_associate_v2].instances[*].attributes.floating_ip"
        )
        return [match.value for match in parser.find(self.__tf_state)]

    def get_state_summary(self):
        return {
            "cluster_name": self.__get_cluster_name(),
            "domain": self.__get_domain(),
            "image": self.__get_image(),
            "nb_users": self.__get_nb_users(),
            "instances": self.__get_instances(),
            "storage": self.__get_storage(),
            "public_keys": self.__get_public_keys(),
            "guest_passwd": self.__get_guest_passwd(),
            "os_floating_ips": self.__get_os_floating_ips(),
        }
