from flask import Flask, send_file, send_from_directory
from flask_restful import Api
from resources.magic_castle_resource import MagicCastleResource
from resources.magic_castle_list_resource import MagicCastleListResource
from resources.magic_castle_status_resource import MagicCastleStatusResource
from resources.available_resources_resource import AvailableResourcesResource
from resources.available_resources_list_resource import AvailableResourcesListResource
from flask_cors import CORS

magic_castle_status = "idle"

app = Flask(__name__)
# Allows all origins on all routes (not safe for production)
CORS(app)

api = Api(app, prefix="/api")
api.add_resource(MagicCastleListResource, "/magic-castle")
api.add_resource(MagicCastleResource, "/magic-castle/<string:cluster_name>")
api.add_resource(
    MagicCastleStatusResource, "/magic-castle/<string:cluster_name>/status"
)
api.add_resource(AvailableResourcesListResource, "/available-resources")
api.add_resource(
    AvailableResourcesResource, "/available-resources/<string:cluster_name>"
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
