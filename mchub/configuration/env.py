from os import path, environ, getcwd

# Paths and filenames
RUN_PATH = environ.get("MCH_RUN_PATH", getcwd())
CLUSTERS_PATH = environ.get("MCH_CLUSTERS_PATH", path.join(RUN_PATH, "clusters"))
DIST_PATH = environ.get("MCH_DIST_PATH", path.join(RUN_PATH, "dist"))
DATABASE_PATH = environ.get("MCH_DATABASE_PATH", path.join(RUN_PATH, "database"))
CONFIGURATION_FILE_PATH = environ.get("MCH_CONFIGURATION_FILE_PATH", RUN_PATH)