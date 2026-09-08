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
        "jupyterhub": {
            "label": "JupyterHub",
            "subdomain": "jupyter",
            "expected_status": 405,
        },
        "freeipa": {
            "label": "FreeIPA",
            "subdomain": "ipa",
            "expected_status": 301,
        },
        "mokey": {
            "label": "Mokey",
            "subdomain": "mokey",
            "expected_status": 405,
        },
    }

    @classmethod
    def check_services(cls, hostname):
        statuses = {}
        for service, config in cls.SERVICES.items():
            url = f"https://{config['subdomain']}.{hostname}"
            try:
                response = requests.head(url, timeout=0.1, verify=True)
                status = (
                    "healthy"
                    if response.status_code == config["expected_status"]
                    else "unavailable"
                )
            except RequestException:
                status = "unavailable"
            statuses[service] = {
                "label": config["label"],
                "url": url,
                "status": status,
            }
        return statuses

    @staticmethod
    def service_is_healthy(service):
        return service["status"] == "healthy"

    @classmethod
    def check_online(cls, hostname):
        return all(
            cls.service_is_healthy(service)
            for service in cls.check_services(hostname).values()
        )

    @staticmethod
    def get_health(service_statuses):
        if not service_statuses:
            return "unknown"

        healthy_services = sum(
            ProvisioningManager.service_is_healthy(service)
            for service in service_statuses.values()
        )
        if healthy_services == len(service_statuses):
            return "healthy"
        if healthy_services == 0:
            return "unavailable"
        return "degraded"
