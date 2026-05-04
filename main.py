from __future__ import annotations

import json
import logging

from config.settings import load_settings
from services.monitoring import run_monitoring_once
from utils import configure_logging


def main() -> None:
    configure_logging()
    settings = load_settings()
    results = run_monitoring_once(settings)

    for result in results:
        logging.info(
            "%s module %s: %s items",
            result.monitor.label,
            result.monitor.module_id,
            len(result.items),
        )


if __name__ == "__main__":
    main()
