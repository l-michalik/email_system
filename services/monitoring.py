from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests

from clients import CrmClient, CrmItem
from config.constants import MONITORED_MODULES, POLL_WINDOW_MINUTES
from config.settings import AppSettings
from schemas.monitoring import ModuleMonitor, MonitoringResult
from services.email_notifications import process_recent_briefs, process_review_jobs
from utils.monitoring import build_query, cutoff_timestamp

logger = logging.getLogger(__name__)


def run_monitoring_once(settings: AppSettings) -> list[MonitoringResult]:
    logger.info("Starting monitoring pass")
    cutoff = cutoff_timestamp()
    brief_monitor, job_monitor = MONITORED_MODULES

    with requests.Session() as session:
        client = CrmClient(settings, session)
        token = client.get_token()

        brief_items = _fetch_monitor_items(client, token, brief_monitor, cutoff)
        process_recent_briefs(brief_items)

        job_window_start = _poll_window_start("jobs")
        job_items = _fetch_monitor_items(client, token, job_monitor, cutoff)
        process_review_jobs(job_items, job_window_start)

    logger.info("Finished monitoring pass")
    return [
        MonitoringResult(monitor=brief_monitor, items=brief_items),
        MonitoringResult(monitor=job_monitor, items=job_items),
    ]


def _fetch_monitor_items(
    client: CrmClient,
    token: str,
    monitor: ModuleMonitor,
    cutoff: str,
) -> list[CrmItem]:
    _log_fetch_window(monitor.label)
    query = build_query(
        monitor.module_id,
        monitor.query_field_name,
        monitor.fields,
        cutoff,
        monitor.select_all_fields,
    )
    items = client.fetch_all_pages(token, query)
    logger.info(
        "Fetched %s %s items from CRM module %s",
        len(items),
        monitor.label,
        monitor.module_id,
    )
    return items


def _poll_window_start(label: str) -> datetime:
    window_end = datetime.now()
    window_start = window_end - timedelta(minutes=POLL_WINDOW_MINUTES)
    logger.info(
        "Processing %s modified between %s and %s",
        label,
        window_start.strftime("%Y-%m-%d %H:%M"),
        window_end.strftime("%Y-%m-%d %H:%M"),
    )
    return window_start


def _log_fetch_window(label: str) -> None:
    window_end = datetime.now()
    window_start = window_end - timedelta(minutes=POLL_WINDOW_MINUTES)
    logger.info(
        "Fetching %s modified between %s and %s (last %s minutes)",
        label,
        window_start.strftime("%Y-%m-%d %H:%M"),
        window_end.strftime("%Y-%m-%d %H:%M"),
        POLL_WINDOW_MINUTES,
    )
