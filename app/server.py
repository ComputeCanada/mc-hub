from flask import Flask, send_file, send_from_directory
from resources.magic_castle_api import MagicCastleAPI
from resources.progress_api import ProgressAPI
from resources.available_resources_api import AvailableResourcesApi
from flask_cors import CORS
from models.openstack_manager import OpenStackManager

OpenStackManager.test_connection()

app = Flask(__name__)
# Allows all origins on all routes (not safe for production)
CORS(app)

magic_castle_view = MagicCastleAPI.as_view("magic_castle")
app.add_url_rule(
    "/api/magic-castle",
    view_func=magic_castle_view,
    defaults={"hostname": None},
    methods=["HEAD", "GET", "POST"],
)
app.add_url_rule(
    "/api/magic-castle/<string:hostname>",
    view_func=magic_castle_view,
    methods=["GET", "DELETE", "PUT"],
)
app.add_url_rule(
    "/api/magic-castle/<string:hostname>/apply",
    view_func=magic_castle_view,
    defaults={"apply": True},
    methods=["POST"],
)

progress_view = ProgressAPI.as_view("progress")
app.add_url_rule(
    "/api/magic-castle/<string:hostname>/status",
    view_func=progress_view,
    methods=["GET"],
)

available_resources_view = AvailableResourcesApi.as_view("available_resources")
app.add_url_rule(
    "/api/available-resources",
    view_func=available_resources_view,
    defaults={"hostname": None},
    methods=["GET"],
)
app.add_url_rule(
    "/api/available-resources/<string:hostname>",
    view_func=available_resources_view,
    methods=["GET"],
)


@app.route("/css/<path:path>")
def send_css_file(path):
    return send_from_directory("../dist/css", path)


@app.route("/js/<path:path>")
def send_js_file(path):
    return send_from_directory("../dist/js", path)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    return send_file("../dist/index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
