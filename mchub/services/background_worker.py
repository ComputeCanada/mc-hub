"""Supervise independent scheduled workers; restart a failed worker with backoff."""
import fcntl
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Event

from ..configuration.env import DATABASE_PATH
from .worker_logging import configure_worker_logging

logger = logging.getLogger(__name__)
MODULES = ("mchub.services.usage_monitor", "mchub.services.cull_expired_cluster", "mchub.services.benchmark_runner", "mchub.services.service_status_monitor", "mchub.services.notification_worker")


class Supervisor:
    def __init__(self, modules=MODULES):
        self.stopping = Event()
        self.children = {module: {"process": None, "retry_at": 0, "delay": 1, "started_at": 0}
                         for module in modules}

    def tick(self):
        now = time.monotonic()
        for module, child in self.children.items():
            if self.stopping.is_set():
                return
            process = child["process"]
            if process is not None:
                code = process.poll()
                if code is None:
                    continue
                logger.error("Worker %s exited with code %s", module, code)
                child["process"] = None
                if now - child["started_at"] >= 60:
                    child["delay"] = 1
                child["retry_at"] = now + child["delay"]
                child["delay"] = min(60, child["delay"] * 2)
            if now < child["retry_at"]:
                continue
            try:
                child["process"] = subprocess.Popen([sys.executable, "-m", module])
                child["started_at"] = now
                logger.info("Started worker %s (pid %s)", module, child["process"].pid)
            except OSError:
                logger.exception("Could not start worker %s", module)
                child["retry_at"] = now + child["delay"]
                child["delay"] = min(60, child["delay"] * 2)

    def shutdown(self):
        self.stopping.set()
        processes = [child["process"] for child in self.children.values() if child["process"] is not None]
        for process in processes:
            if process.poll() is None:
                process.terminate()
        deadline = time.monotonic() + 10
        for process in processes:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def run(self):
        try:
            while not self.stopping.is_set():
                self.tick()
                self.stopping.wait(1)
        finally:
            self.shutdown()


def main():
    configure_worker_logging()
    # Prevent a second supervisor from starting duplicate workers on this volume.
    with (Path(DATABASE_PATH) / "background-worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A background worker already owns this database volume")
        supervisor = Supervisor()
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: supervisor.stopping.set())
        supervisor.run()


if __name__ == "__main__":
    main()
