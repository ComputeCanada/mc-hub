"""Deliver the durable outbox independently of provider polling."""
import logging
import signal
from threading import Event

from .. import create_app
from ..database import db
from .notifications import deliver_once
from .worker_logging import configure_worker_logging


def main():
    configure_worker_logging()
    stopping = Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopping.set())
    app = create_app()
    while not stopping.is_set():
        with app.app_context():
            try:
                deliver_once()
            except Exception:
                db.session.rollback()
                logging.getLogger(__name__).error("Notification delivery database operation failed")
            finally:
                db.session.remove()
        stopping.wait(5)


if __name__ == "__main__":
    main()
