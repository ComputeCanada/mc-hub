from flask import Flask, send_file, send_from_directory, jsonify
from flask_restful import Api
from resources.magic_castle import MagicCastle
from resources.magic_castle_list import MagicCastleList
from resources.magic_castle_status import MagicCastleStatus
from flask_cors import CORS

magic_castle_status = "idle"

app = Flask(__name__)
# Allows all origins on all routes (not safe for production)
CORS(app)

api = Api(app, prefix="/api")
api.add_resource(MagicCastleList, "/magic-castle")
api.add_resource(MagicCastle, "/magic-castle/<string:cluster_name>")
api.add_resource(MagicCastleStatus, "/magic-castle/<string:cluster_name>/status")


@app.route("/")
def index():
    return send_file("static/index.html")


@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
