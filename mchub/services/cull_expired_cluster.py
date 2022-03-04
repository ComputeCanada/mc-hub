import logging
import time

from datetime import datetime
from os import environ

from requests import get, delete, post
from requests.exceptions import RequestException
from requests.compat import urljoin

MC_API_PATH = "api/magic-castles"
MC_EXPIRATON_FORMAT = "%Y-%m-%d"

logging.basicConfig(level=logging.INFO)

def main(host="127.0.0.1", port=5000, interval=3600):
    host = f"http://{host}:{port}"
    mc_api = urljoin(host, MC_API_PATH)
    logging.info(f"Connecting to {mc_api}")
    while True:
        now = datetime.now()
        logging.info(f"Looking for expired clusters at {now}")
        try:
            clusters = get(mc_api).json()
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
            exp_date = datetime.strptime(cluster["expiration_date"], MC_EXPIRATON_FORMAT)
            if exp_date < now:
                hostname = cluster["hostname"]
                host_api = urljoin(f"{mc_api}/", hostname)
                apply_api = urljoin(f"{host_api}/", "apply")
                logging.info(f"Cluster {hostname} is expired - deleting")
                try:
                    delete(host_api)
                except RequestException as e:
                    logging.error(f"Error while planning {cluster['hostname']} deletion - {e}")
                    continue

                try:
                    post(apply_api)
                except RequestException as e:
                    logging.error(f"Error while deleting {cluster['hostname']} deletion - {e}")
            else:
                continue
        time.sleep(interval)


if __name__ == "__main__":
    host = environ.get('MCHUB_HOST', '127.0.0.1')
    port = environ.get('MCHUB_PORT', 5000)
    main(host=host, port=port)
