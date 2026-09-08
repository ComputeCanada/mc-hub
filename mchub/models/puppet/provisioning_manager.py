import requests

from requests.exceptions import RequestException

MAX_PROVISIONING_TIME = 3600


class ProvisioningManager:
    """
    ProvisioningManager is responsible checking the provisioning status of a cluster.

    ProvisioningManager sends GET requests to HTTP services created by Magic Castle via
    its check_online() method. If the method returns False, the provisioning is yet
    completed, if it returns True, the services are online and the cluster is most
    likely online.
    """

    SERVICES = {
        "jupyterhub": ("jupyter", 405),
        "freeipa": ("ipa", 301),
        "mokey": ("mokey", 405),
    }

    @classmethod
    def check_services(cls, hostname):
        statuses = {}
        for service, (subdomain, expected_status) in cls.SERVICES.items():
            try:
                response = requests.head(
                    f"https://{subdomain}.{hostname}", timeout=0.1, verify=True
                )
                statuses[service] = (
                    "healthy"
                    if response.status_code == expected_status
                    else "unavailable"
                )
            except RequestException:
                statuses[service] = "unavailable"
        return statuses

    @classmethod
    def check_online(cls, hostname):
        return all(
            status == "healthy"
            for status in cls.check_services(hostname).values()
        )

    @staticmethod
    def get_health(service_statuses):
        if not service_statuses:
            return "unknown"

        healthy_services = sum(
            status == "healthy" for status in service_statuses.values()
        )
        if healthy_services == len(service_statuses):
            return "healthy"
        if healthy_services == 0:
            return "unavailable"
        return "degraded"
