from os import path as os_path

from flask import Flask, send_file, send_from_directory
from flask_cors import CORS


def create_app(db_path=None):
    from .configuration import get_config, DATABASE_FILENAME
    from .configuration.env import DIST_PATH, DATABASE_PATH
    from .database import db
    from .resources.magic_castle_api import MagicCastleAPI
    from .resources.progress_api import ProgressAPI
    from .resources.available_resources_api import AvailableResourcesAPI
    from .resources.domains_api import DomainsAPI
    from .resources.user_api import UserAPI
    from .resources.project_api import ProjectAPI
    from .resources.template_api import TemplateAPI

    if db_path is None:
        db_path = f"sqlite:///{DATABASE_PATH}/{DATABASE_FILENAME}"
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # Allows origins set in config file on all routes
    CORS(
        app,
        origins=get_config()["cors_allowed_origins"],
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

    domains_view = DomainsAPI.as_view("domains")
    app.add_url_rule(
        "/api/domains/",
        view_func=domains_view,
        methods=["GET"],
    )

    available_resources_view = AvailableResourcesAPI.as_view("available_resources")
    app.add_url_rule(
        "/api/available-resources/host/<string:hostname>",
        view_func=available_resources_view,
        defaults={"cloud_id": None},
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/available-resources/cloud/<string:cloud_id>",
        view_func=available_resources_view,
        defaults={"hostname": None},
        methods=["GET"],
    )

    template_view = TemplateAPI.as_view("template")
    app.add_url_rule(
        "/api/template/<string:template_name>",
        view_func=template_view,
        methods=["GET"],
    )

    user_view = UserAPI.as_view("user")
    app.add_url_rule("/api/users/me", view_func=user_view, methods=["GET"])

    project_view = ProjectAPI.as_view("projects")
    app.add_url_rule(
        "/api/projects",
        view_func=project_view,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/api/projects/<int:id>",
        view_func=project_view,
        methods=["GET", "PATCH", "DELETE"],
    )

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

    return app
