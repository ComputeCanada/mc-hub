import requests

from requests.exceptions import ConnectionError

MAX_PROVISIONING_TIME = 3600


class ProvisioningManager:
    """
    ProvisioningManager is responsible checking the provisioning status of a cluster.

    ProvisioningManager sends GET requests to HTTP services created by Magic Castle via
    its check_online() method. If the method returns False, the provisioning is yet
    completed, if it returns True, the services are online and the cluster is most
    likely online.
    """
    @classmethod
    def check_online(self, hostname):
        try:
            return (
                requests.head(f"https://jupyter.{hostname}", timeout=0.1).status_code == 405 and
                requests.head(f"https://ipa.{hostname}", timeout=0.1).status_code == 301     and
                requests.head(f"https://mokey.{hostname}", timeout=0.1).status_code == 405
            )
        except ConnectionError:
            return False