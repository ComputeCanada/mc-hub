from . import create_app
from . configuration import config

if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=config["port"],
        debug=config["debug"]
    )
