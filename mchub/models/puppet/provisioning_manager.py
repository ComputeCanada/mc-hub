import time

import requests

from requests.exceptions import ConnectionError

from ... exceptions.server_exception import PuppetTimeoutException

MAX_PROVISIONING_TIME = 3600
POLL_INTERVAL = 30


class ProvisioningManager:
    """
    ProvisioningManager is responsible for monitoring the provisioning status of a single cluster.

    To do so, ProvisioningManager periodically sends GET requests to HTTP services created by Magic Castle until
    they all send a valid response, meaning the provisioning is probably finished.
    """

    # Contains the hostnames of clusters currently being polled
    # to avoid multiple threads from polling the same cluster
    __busy_hostnames = set()

    def __init__(self, hostname):
        self.__hostname = hostname

    def is_busy(self):
        return self.__hostname in ProvisioningManager.__busy_hostnames

    def poll_until_success(self):
        if not self.is_busy():
            ProvisioningManager.__busy_hostnames.add(self.__hostname)
            provisioning_success = False
            start_time = time.time()
            while not provisioning_success:
                if time.time() - start_time > MAX_PROVISIONING_TIME:
                    raise PuppetTimeoutException
                try:
                    provisioning_success = (
                        requests.get(f"https://jupyter.{self.__hostname}").status_code
                        == 200
                        and requests.get(f"https://ipa.{self.__hostname}").status_code
                        == 200
                        and requests.get(f"https://mokey.{self.__hostname}").status_code
                        == 200
                    )
                except ConnectionError:
                    pass

                time.sleep(POLL_INTERVAL)
            ProvisioningManager.__busy_hostnames.remove(self.__hostname)
