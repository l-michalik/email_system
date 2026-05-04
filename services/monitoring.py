from __future__ import annotations

import requests

from config.constants import MONITORED_MODULES
from config.settings import AppSettings
from schemas.monitoring import MonitoringResult
from utils import get_token
from utils.monitoring import build_query, cutoff_timestamp, fetch_all_pages


def run_monitoring_once(settings: AppSettings) -> list[MonitoringResult]:
    cutoff = cutoff_timestamp()

    with requests.Session() as session:
        token = get_token()

        results: list[MonitoringResult] = []
        for monitor in MONITORED_MODULES:
            query = build_query(monitor.module_id, monitor.last_modified_field_id, cutoff)
            items = fetch_all_pages(session, settings.search_url, token, query)
            results.append(MonitoringResult(monitor=monitor, items=items))

        return results
