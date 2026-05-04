from __future__ import annotations

from datetime import datetime, timedelta

import requests

from config.constants import (
    BRIEF_CREATED_BY_CHATBOT_FIELD_NAME,
    BRIEF_CREATED_BY_CHATBOT_VALUE,
    BRIEF_CREATED_DATE_FIELD_NAME,
    MONITORED_MODULES,
    POLL_WINDOW_MINUTES,
)
from config.settings import AppSettings
from schemas.monitoring import MonitoringResult
from utils import get_token
from utils.monitoring import (
    build_query,
    cutoff_timestamp,
    fetch_all_pages,
    get_field_value,
    parse_brief_created_date,
    send_brief_creation_email,
)


def run_monitoring_once(settings: AppSettings) -> list[MonitoringResult]:
    cutoff = cutoff_timestamp()
    created_cutoff = datetime.now() - timedelta(minutes=POLL_WINDOW_MINUTES)

    with requests.Session() as session:
        token = get_token()

        results: list[MonitoringResult] = []
        for monitor in MONITORED_MODULES:
            query = build_query(
                monitor.module_id,
                monitor.query_field_name,
                monitor.fields,
                cutoff,
            )
            items = fetch_all_pages(session, settings.search_url, token, query)

            if monitor.label == "brief":
                for item in items:
                    if (
                        get_field_value(item, BRIEF_CREATED_BY_CHATBOT_FIELD_NAME)
                        != BRIEF_CREATED_BY_CHATBOT_VALUE
                    ):
                        continue
                    send_brief_creation_email(item)
                    created_at = parse_brief_created_date(
                        get_field_value(item, BRIEF_CREATED_DATE_FIELD_NAME)
                    )
                    if created_at < created_cutoff:
                        continue

            results.append(MonitoringResult(monitor=monitor, items=items))

        return results
