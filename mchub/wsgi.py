from . import create_app
from .configuration import get_config

if __name__ == "__main__":
    app = create_app()
    config = get_config()
    app.run(host="0.0.0.0", port=config["port"], debug=config["debug"])
