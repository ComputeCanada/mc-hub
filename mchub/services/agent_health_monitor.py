"""Monitor configured pools even when no browser is connected."""
import signal
from threading import Event

from .. import create_app
from .agent_health import poll_once, RECOVERY_INTERVAL
from .worker_logging import configure_worker_logging


def main():
    configure_worker_logging()
    stopping = Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stopping.set())
    app = create_app()
    while not stopping.is_set():
        with app.app_context():
            poll_once()
        stopping.wait(RECOVERY_INTERVAL)


if __name__ == "__main__":
    main()
