import time
from exceptions.puppet_timeout_exception import PuppetTimeoutException
import requests
from requests.exceptions import ConnectionError
import logging

MAX_PROVISIONING_TIME = 3600
POLL_INTERVAL = 2


class ProvisioningManager:
    def __init__(self, hostname):
        self.__hostname = hostname

    def poll_until_success(self):
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
