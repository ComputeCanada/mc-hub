from . import create_app
from .database.cleanup_manager import CleanupManager

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        CleanupManager.clean_status()
