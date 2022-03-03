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

    def __init__(self, hostname):
        self.hostname = hostname

    def check_online(self):
        try:
            return all ((
                requests.get(f"https://jupyter.{self.hostname}").status_code == 200,
                requests.get(f"https://ipa.{self.hostname}").status_code == 200,
                requests.get(f"https://mokey.{self.hostname}").status_code == 200,
            ))
        except ConnectionError:
            return False
