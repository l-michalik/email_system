from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
