from os import environ

from openstack.config.loader import OpenStackConfig

ALL_CLOUD_ID = [cloud.name for cloud in OpenStackConfig().get_all_clouds()]
DEFAULT_CLOUD = environ.get("OS_CLOUD", ALL_CLOUD_ID[0])
