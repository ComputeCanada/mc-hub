"""Before starting MC-Hub, we have to verify that clusters with a
main.tf.json have their plugin folder correctly initialized. To do
this, we scan the clusters folder and call terraform init in each
folder with a main.tf.json.
"""

import argparse

from os import scandir, path, exit
from subprocess import run
from logging import getLogger

from .configuration.env import CLUSTERS_PATH

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan CLUSTERS_PATH and initialized all clusters with terraform"
    )
    parser.add_argument("--upgrade", action="store_true")
    arguments = parser.parse_args()

    logger = getLogger()
    for fd in scandir(CLUSTERS_PATH):
        if fd.is_dir():
            cmd_args = ["terraform", "init", "-no-color", "-input=false"]
            if parser.upgrade:
                cmd_args += ["-upgrade"]
            try:
                cmd = run(
                    cmd_args,
                    cwd=path.join(CLUSTERS_PATH, fd),
                    check=True,
                    capture_output=True,
                )
            except Exception as error:
                logger.error("Could not initialize cluster folder {}".format(fd))
                logger.debug(error)
                logger.debug(cmd.stderr)
                logger.debug(cmd.stdout)
                exit(1)
