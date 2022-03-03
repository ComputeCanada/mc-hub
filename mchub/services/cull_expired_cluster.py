from datetime import datetime

import logging
import time

from requests import get, delete
from requests.exceptions import RequestException
from requests.compat import urljoin

MC_API_PATH = "api/magic-castles"
MC_EXPIRATON_FORMAT = "%Y-%m-%d"

logging.basicConfig(level=logging.INFO)

def main(ip="127.0.0.1", port=5000, interval=3600):
    host = f"http://{ip}:{port}"
    mc_api = urljoin(host, MC_API_PATH)
    while True:
        now = datetime.now()
        logging.info(f"Looking for expired clusters at {now}")
        try:
            clusters = get(mc_api).json()
        except :
            clusters = []
        for cluster in clusters:
            exp_date = datetime.strptime(cluster["expiration_date"], MC_EXPIRATON_FORMAT)
            if exp_date < now:
                hostname = cluster["hostname"]
                host_api = urljoin(f"{mc_api}/", hostname)
                logging.info(f"Cluster {hostname} is expired - deleting")
                try:
                    delete(host_api)
                except RequestException as e:
                    logging.error(f"Error while deleting {cluster['hostname']} - {e}")
            else:
                continue
        time.sleep(interval)


if __name__ == "__main__":
    main()