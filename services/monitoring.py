from __future__ import annotations

import logging
from datetime import UTC, datetime

import requests

from clients import CrmClient, CrmItem
from config.constants import MONITORED_MODULES
from config.settings import AppSettings
from schemas.monitoring import ModuleMonitor, MonitoringResult
from services.email_notifications import process_recent_briefs, process_review_jobs
from utils.brief_storage import get_sync_checkpoint, set_sync_checkpoint
from utils.monitoring import build_query, cutoff_timestamp

logger = logging.getLogger(__name__)


def run_monitoring_once(settings: AppSettings) -> list[MonitoringResult]:
    logger.info("Starting monitoring pass")
    sync_started_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    brief_monitor, job_monitor = MONITORED_MODULES

    with requests.Session() as session:
        client = CrmClient(settings, session)
        token = client.get_token()

        brief_cutoff = _monitor_cutoff(brief_monitor)
        brief_items = _fetch_monitor_items(client, token, brief_monitor, brief_cutoff)
        process_recent_briefs(settings, brief_items)
        set_sync_checkpoint(brief_monitor.label, sync_started_at)

        job_cutoff = _monitor_cutoff(job_monitor)
        job_items = _fetch_monitor_items(client, token, job_monitor, job_cutoff)
        process_review_jobs(settings, job_items)
        set_sync_checkpoint(job_monitor.label, sync_started_at)

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
    _log_fetch_window(monitor.label, cutoff)
    query = build_query(
        monitor.module_id,
        monitor.query_field_name,
        monitor.fields,
        cutoff,
        monitor.select_all_fields,
        monitor.filter_condition,
    )
    items = client.fetch_all_pages(token, query)
    logger.info(
        "Fetched %s %s items from CRM module %s",
        len(items),
        monitor.label,
        monitor.module_id,
    )
    return items


def _monitor_cutoff(monitor: ModuleMonitor) -> str:
    checkpoint = get_sync_checkpoint(monitor.label)
    if checkpoint is not None:
        return checkpoint
    return cutoff_timestamp()


def _log_fetch_window(label: str, cutoff: str) -> None:
    logger.info("Fetching %s records modified since %s", label, cutoff)
