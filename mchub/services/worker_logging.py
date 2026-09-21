"""Consistent UTC logging for the supervisor and its worker processes."""
import logging
import time


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def configure_worker_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(UTCFormatter(
        "%(asctime)s.%(msecs)03dZ %(levelname)s [pid=%(process)d] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
