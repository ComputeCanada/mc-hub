from os import path, environ, getcwd

# Paths and filenames
RUN_PATH = environ.get("MCH_RUN_PATH", getcwd())
CLUSTERS_PATH = environ.get("MCH_CLUSTERS_PATH", path.join(RUN_PATH, "clusters"))
APP_PATH = environ.get("MCH_APP_PATH", path.join(RUN_PATH, "mchub"))
DIST_PATH = environ.get("MCH_DIST_PATH", path.join(RUN_PATH, "dist"))
DATABASE_PATH = environ.get("MCH_DATABASE_PATH", path.join(RUN_PATH, "database"))
SCHEMA_MIGRATIONS_DIRECTORY = path.join(APP_PATH, "database", "migrations")
CONFIGURATION_FILE_PATH = environ.get("MCH_CONFIGURATION_FILE_PATH", RUN_PATH)