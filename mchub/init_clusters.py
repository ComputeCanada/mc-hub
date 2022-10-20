"""Before starting MC-Hub, we have to verify that clusters with a
main.tf.json have their plugin folder correctly initialized. To do
this, we scan the clusters folder and call terraform init in each
folder with a main.tf.json.
"""

import argparse

from os import scandir, path
from subprocess import run

from .configuration.env import CLUSTERS_PATH

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan CLUSTERS_PATH and initialized all clusters with terraform"
    )
    arguments = parser.parse_args()
    for fd in scandir(CLUSTERS_PATH):
        if fd.is_dir():
            # Initialize terraform modules
            try:
                run(
                    ["terraform", "init", "-no-color", "-input=false"],
                    cwd=path.join(CLUSTERS_PATH, fd),
                    check=True,
                )
            except Exception as error:
                pass
