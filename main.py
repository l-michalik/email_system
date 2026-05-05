from __future__ import annotations

from config.logging import configure_logging
from config.settings import load_settings
from services.monitoring import run_monitoring_once


def main() -> None:
    configure_logging()
    settings = load_settings()
    run_monitoring_once(settings)


if __name__ == "__main__":
    main()
