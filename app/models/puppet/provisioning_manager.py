import time
from exceptions.puppet_timeout_exception import PuppetTimeoutException
import requests
from requests.exceptions import ConnectionError
import logging

MAX_PROVISIONING_TIME = 3600
POLL_INTERVAL = 2


class ProvisioningManager:
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
                    )
                except requests.exceptions.ConnectionError:
                    pass

                time.sleep(POLL_INTERVAL)
            ProvisioningManager.__busy_hostnames.remove(self.__hostname)
