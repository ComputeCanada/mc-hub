import logging
import time

from datetime import datetime
from os import environ

from requests import get, delete, post
from requests.exceptions import RequestException
from requests.compat import urljoin

from ..configuration import get_config
from ..models.auth_type import AuthType
from ..models.magic_castle.cluster_status_code import ClusterStatusCode

MC_API_PATH = "api/magic-castles"
MC_EXPIRATON_FORMAT = "%Y-%m-%d"
PLAN_POLL_INTERVAL = 10
PLAN_WAIT_TIMEOUT = 5 * 60

logging.basicConfig(level=logging.INFO)


def wait_for_destroy_plan(host_api, headers):
    status_api = urljoin(f"{host_api}/", "status")
    deadline = time.monotonic() + PLAN_WAIT_TIMEOUT

    while time.monotonic() < deadline:
        response = get(status_api, headers=headers)
        response.raise_for_status()
        status = response.json().get("status")

        if status == ClusterStatusCode.CREATED:
            return True
        if status == ClusterStatusCode.NOT_FOUND:
            # Clusters without a Terraform workspace are deleted immediately.
            return False
        if status in (
            ClusterStatusCode.PLAN_ERROR,
            ClusterStatusCode.DESTROY_ERROR,
        ):
            raise RuntimeError(f"Destroy plan failed with status {status}")

        time.sleep(PLAN_POLL_INTERVAL)

    raise TimeoutError("Timed out waiting for the destroy plan")


def main(host="127.0.0.1", port=5000, interval=3600):
    host = f"http://{host}:{port}"
    mc_api = urljoin(host, MC_API_PATH)
    logging.info(f"Connecting to {mc_api}")
    headers = {}
    if AuthType.TOKEN in get_config()["auth_type"]:
        headers["Authorization"] = f"token {get_config()['token']}"
    while True:
        now = datetime.now()
        logging.info(f"Looking for expired clusters at {now}")

        try:
            clusters = get(mc_api, headers=headers).json()
        except RequestException as e:
            logging.warning("Could not reach the API - 30 seconds pause.")
            time.sleep(30)
            continue
        except Exception as e:
            clusters = []
            logging.error(e)

        for cluster in clusters:
            if cluster["expiration_date"] is None:
                continue
            exp_date = datetime.strptime(
                cluster["expiration_date"], MC_EXPIRATON_FORMAT
            )
            if exp_date < now:
                hostname = cluster["hostname"]
                host_api = urljoin(f"{mc_api}/", hostname)
                apply_api = urljoin(f"{host_api}/", "apply")
                logging.info(f"Cluster {hostname} is expired - deleting")
                try:
                    delete_response = delete(host_api, headers=headers)
                    delete_response.raise_for_status()
                    if not wait_for_destroy_plan(host_api, headers):
                        continue
                except (RequestException, RuntimeError, TimeoutError) as e:
                    logging.error(
                        f"Error while planning {cluster['hostname']} deletion - {e}"
                    )
                    continue

                try:
                    apply_response = post(apply_api, headers=headers)
                    apply_response.raise_for_status()
                except RequestException as e:
                    logging.error(
                        f"Error while deleting {cluster['hostname']} deletion - {e}"
                    )
            else:
                continue
        time.sleep(interval)


if __name__ == "__main__":
    host = environ.get("MCHUB_HOST", "127.0.0.1")
    port = environ.get("MCHUB_PORT", 5000)
    main(host=host, port=port)
