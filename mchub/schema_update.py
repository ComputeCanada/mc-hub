import argparse

from os import path

from . import create_app
from .database import db
from .database.cleanup_manager import CleanupManager

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Updates the database schema with the new schema migrations."
    )
    parser.add_argument("--clean", action="store_true")
    arguments = parser.parse_args()

    app = create_app()
    with app.app_context():
        if not path.exists(db.engine.url.database):
            print("Database does not exist. Creating...")
            db.create_all()
        elif arguments.clean:
            CleanupManager.clean_status()
