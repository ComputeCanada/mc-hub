from os import path as os_path

from flask import Flask, send_file, send_from_directory
from resources.magic_castle_api import MagicCastleAPI
from resources.progress_api import ProgressAPI
from resources.available_resources_api import AvailableResourcesApi
from resources.user_api import UserAPI
from flask_cors import CORS
from database.schema_manager import SchemaManager
from database.database_manager import DatabaseManager
from models.configuration import config

from models.constants import DIST_PATH

# Update the database schema to the latest version
with DatabaseManager.connect() as database_connection:
    SchemaManager(database_connection).update_schema()

app = Flask(__name__)

# Allows origins set in config file on all routes
CORS(
    app,
    origins=config["cors_allowed_origins"],
)

magic_castle_view = MagicCastleAPI.as_view("magic_castle")
app.add_url_rule(
    "/api/magic-castles",
    view_func=magic_castle_view,
    defaults={"hostname": None},
    methods=["HEAD", "GET", "POST"],
)
app.add_url_rule(
    "/api/magic-castles/<string:hostname>",
    view_func=magic_castle_view,
    methods=["GET", "DELETE", "PUT"],
)
app.add_url_rule(
    "/api/magic-castles/<string:hostname>/apply",
    view_func=magic_castle_view,
    defaults={"apply": True},
    methods=["POST"],
)

progress_view = ProgressAPI.as_view("progress")
app.add_url_rule(
    "/api/magic-castles/<string:hostname>/status",
    view_func=progress_view,
    methods=["GET"],
)

available_resources_view = AvailableResourcesApi.as_view("available_resources")
app.add_url_rule(
    "/api/available-resources",
    view_func=available_resources_view,
    defaults={"hostname": None, "cloud_id": None},
    methods=["GET"],
)
app.add_url_rule(
    "/api/available-resources/<string:hostname>",
    view_func=available_resources_view,
    methods=["GET"],
)

user_view = UserAPI.as_view("user")
app.add_url_rule("/api/users/me", view_func=user_view, methods=["GET"])


@app.route("/css/<path:path>")
def send_css_file(path):
    return send_from_directory(os_path.join(DIST_PATH, "css"), path)


@app.route("/js/<path:path>")
def send_js_file(path):
    return send_from_directory(os_path.join(DIST_PATH, "js"), path)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    # Single page application
    response = send_file(os_path.join(DIST_PATH, "index.html"))

    # Avoid caching SPA to avoid showing the page when the user is logged out
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
