from __future__ import annotations

from datetime import UTC, datetime

import requests

from clients import CrmClient, CrmItem
from config.constants import BRIEF_PAGE_SIZE, MONITORED_MODULES
from config.settings import AppSettings
from schemas.monitoring import ModuleMonitor, MonitoringResult
from services.email_notifications import process_recent_briefs, process_review_jobs
from utils.brief_storage import (
    get_chatbot_brief,
    get_sync_checkpoint,
    save_chatbot_brief,
    set_sync_checkpoint,
)
from utils.monitoring import build_query, cutoff_timestamp, get_field_value


def run_monitoring_once(settings: AppSettings) -> list[MonitoringResult]:
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
        _prime_missing_job_briefs(client, token, job_items)
        process_review_jobs(settings, job_items)
        set_sync_checkpoint(job_monitor.label, sync_started_at)

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
    query = build_query(
        monitor.module_id,
        monitor.query_field_name,
        monitor.fields,
        cutoff,
        monitor.select_all_fields,
        monitor.filter_condition,
    )
    return client.fetch_all_pages(token, query)


def _prime_missing_job_briefs(
    client: CrmClient,
    token: str,
    job_items: list[CrmItem],
) -> None:
    seen_briefs: set[str] = set()
    for item in job_items:
        brief_number = get_field_value(item, "Brief Number")
        if not brief_number or brief_number in seen_briefs:
            continue
        seen_briefs.add(brief_number)

        if get_chatbot_brief(brief_number) is not None:
            continue

        query = f"SELECT * FROM MODULE_3 WHERE FD_4660 = '{_escape_crm_literal(brief_number)}'"
        for brief_item in client.fetch_all_pages(token, query, page_size=BRIEF_PAGE_SIZE):
            save_chatbot_brief(brief_item)


def _monitor_cutoff(monitor: ModuleMonitor) -> str:
    checkpoint = get_sync_checkpoint(monitor.label)
    if checkpoint is not None:
        return checkpoint
    return cutoff_timestamp()


def _escape_crm_literal(value: str) -> str:
    return value.replace("'", "''")
