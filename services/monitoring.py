from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

from config.constants import (
    CHANGE_REQUEST_UPDATED_EMAIL_SUBJECT,
    BRIEF_CREATED_DATE_FIELD_NAME,
    BRIEF_EMAIL_SUBJECT,
    BRIEF_LAST_MODIFIED_DATE_FIELD_NAME,
    BRIEF_NUMBER_FIELD_NAME,
    JOB_ASSETS_FIELD_NAME,
    JOB_BRIEF_NUMBER_FIELD_NAME,
    JOB_LAST_MODIFIED_DATE_FIELD_NAME,
    JOB_NAME_FIELD_NAME,
    JOB_NUMBER_FIELD_NAME,
    JOB_OUTPUT_FILES_LINK_FIELD_NAME,
    JOB_STATUS_CLIENT_REVIEW_VALUE,
    JOB_STATUS_FIELD_NAME,
    MONITORED_MODULES,
    POLL_WINDOW_MINUTES,
    WORK_REVIEW_REQUEST_EMAIL_SUBJECT,
)
from config.settings import AppSettings
from schemas.monitoring import MonitoringResult
from utils import get_token
from utils.email_templates import EmailTemplateContent, build_email_html, build_email_text
from utils.mailer import send_email
from utils.brief_storage import (
    should_send_change_request_updated_email,
    update_chatbot_brief,
)
from utils.monitoring import (
    cutoff_timestamp,
    fetch_all_pages,
    get_field_value,
    parse_brief_last_modified_date,
)


def create_brief_creation_email(brief_number: str) -> EmailTemplateContent:
    return EmailTemplateContent(
        subject=BRIEF_EMAIL_SUBJECT,
        title="Brief has been created successfully",
        subtitle=f"Brief Number: {brief_number}",
        body_text=(
            "Please make a note of this Brief ID. If you would like to update or "
            "modify this brief in the future, simply return to the chatbot by "
            "clicking Open Chatbot and reference your Brief ID."
        ),
        button_label="Open Chatbot",
        button_link="https://waa.mdbgo.io/",
    )


def create_brief_update_email(brief_id: str) -> EmailTemplateContent:
    return EmailTemplateContent(
        subject=CHANGE_REQUEST_UPDATED_EMAIL_SUBJECT,
        title="Your change request has been successfully updated",
        subtitle=f"Brief ID: {brief_id}",
        body_text=(
            "We are pleased to inform you that your requested change has been "
            "successfully updated in Joule. To view your updated brief, simply "
            "click on Open Chatbot below and reference your Brief ID."
        ),
        button_label="Open Chatbot",
        button_link="https://waa.mdbgo.io/",
    )


def create_work_review_request_email(
    brief_number: str,
    job_name: str,
    job_number: str,
) -> EmailTemplateContent:
    return EmailTemplateContent(
        subject=WORK_REVIEW_REQUEST_EMAIL_SUBJECT,
        title="Your Asset is Ready for Review",
        subtitle=(
            f"Brief Number: {brief_number}\n"
            f"Job Name: {job_name}\n"
            f"Job Number: {job_number}"
        ),
        body_text=(
            "To review the asset, please click the chatbot link below. You will have "
            "the option to approve or reject it based on your requirements."
        ),
        button_label="Open Chatbot",
        button_link="https://waa.mdbgo.io/",
    )


def build_email_template_content(condition: str, brief_id: str) -> EmailTemplateContent:
    if condition == "brief_created":
        return create_brief_creation_email(brief_id)
    if condition == "change_request_updated":
        return create_brief_update_email(brief_id)
    raise ValueError(f"Unsupported email condition: {condition}")


def send_brief_creation_email(brief_id: str) -> None:
    content = create_brief_creation_email(brief_id)
    send_email(
        content.subject,
        build_email_text(content),
        html_body=build_email_html(content),
    )


def send_change_request_updated_email(brief_id: str) -> None:
    content = create_brief_update_email(brief_id)
    send_email(
        content.subject,
        build_email_text(content),
        html_body=build_email_html(content),
    )


def send_work_review_request_email(
    brief_number: str,
    job_name: str,
    job_number: str,
) -> None:
    content = create_work_review_request_email(brief_number, job_name, job_number)
    send_email(
        content.subject,
        build_email_text(content),
        html_body=build_email_html(content),
    )


def _job_has_review_assets(item: dict[str, Any]) -> bool:
    return bool(
        get_field_value(item, JOB_ASSETS_FIELD_NAME)
        or get_field_value(item, JOB_OUTPUT_FILES_LINK_FIELD_NAME)
    )


def _normalize_status(value: str | None) -> str:
    return (value or "").strip().lower()


def should_send_work_review_request_email(
    item: dict[str, Any],
    window_start: datetime,
) -> bool:
    job_number = get_field_value(item, JOB_NUMBER_FIELD_NAME)
    brief_number = get_field_value(item, JOB_BRIEF_NUMBER_FIELD_NAME)
    last_modified_date = get_field_value(item, JOB_LAST_MODIFIED_DATE_FIELD_NAME)
    status = get_field_value(item, JOB_STATUS_FIELD_NAME)
    if not last_modified_date or not status:
        logging.info(
            "Skipping work review email for job %s: missing last modified date or status (raw last modified=%s, status=%s)",
            job_number or "<unknown>",
            last_modified_date or "<missing>",
            status or "<missing>",
        )
        return False

    modified_at = parse_brief_last_modified_date(last_modified_date)
    if modified_at < window_start:
        logging.info(
            "Skipping work review email for job %s: last modified raw=%s parsed=%s is outside the poll window starting %s",
            job_number or "<unknown>",
            last_modified_date,
            modified_at.strftime("%Y-%m-%d %H:%M"),
            window_start.strftime("%Y-%m-%d %H:%M"),
        )
        return False

    normalized_status = _normalize_status(status)
    if normalized_status not in {
        JOB_STATUS_CLIENT_REVIEW_VALUE,
        "client review",
    }:
        logging.info(
            "Skipping work review email for job %s: status raw=%s, expected CLIENT REVIEW",
            job_number or "<unknown>",
            status,
        )
        return False

    if not _job_has_review_assets(item):
        logging.info(
            "Skipping work review email for job %s: no assets or output files link found",
            job_number or "<unknown>",
        )
        return False

    logging.info(
        "Work review email is eligible for job %s (brief %s, status raw=%s, modified raw=%s parsed=%s)",
        job_number or "<unknown>",
        brief_number or "<unknown>",
        status,
        last_modified_date,
        modified_at.strftime("%Y-%m-%d %H:%M"),
    )
    return True


def _log_fetch_window(label: str) -> tuple[datetime, datetime]:
    window_end = datetime.now()
    window_start = window_end - timedelta(minutes=POLL_WINDOW_MINUTES)
    logging.info(
        "Fetching %s modified between %s and %s (last %s minutes)",
        label,
        window_start.strftime("%H:%M"),
        window_end.strftime("%H:%M"),
        POLL_WINDOW_MINUTES,
    )
    return window_start, window_end


def _process_recent_briefs(
    items: list[dict[str, Any]],
) -> None:
    for item in items:
        created_date = get_field_value(item, BRIEF_CREATED_DATE_FIELD_NAME)
        last_modified_date = get_field_value(item, BRIEF_LAST_MODIFIED_DATE_FIELD_NAME)

        created_at = parse_brief_last_modified_date(created_date)
        modified_at = parse_brief_last_modified_date(last_modified_date)

        if modified_at == created_at:
            brief_id = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
            send_brief_creation_email(brief_id)
        elif should_send_change_request_updated_email(item):
            brief_id = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
            send_change_request_updated_email(brief_id)
            update_chatbot_brief(item)


def run_monitoring_once(settings: AppSettings) -> list[MonitoringResult]:
    cutoff = cutoff_timestamp()
    brief_monitor, job_monitor = MONITORED_MODULES

    with requests.Session() as session:
        token = get_token()

        results: list[MonitoringResult] = []
        _log_fetch_window("briefs")
        brief_query = (
            f"SELECT * FROM MODULE_{brief_monitor.module_id} "
            f"WHERE {brief_monitor.fields[brief_monitor.query_field_name]} > '{cutoff}'"
        )
        brief_items = fetch_all_pages(session, settings.search_url, token, brief_query)
        _process_recent_briefs(brief_items)
        results.append(MonitoringResult(monitor=brief_monitor, items=brief_items))

        job_window_start, _ = _log_fetch_window("jobs")
        job_query = (
            f"SELECT * FROM MODULE_{job_monitor.module_id} "
            f"WHERE {job_monitor.fields[job_monitor.query_field_name]} > '{cutoff}'"
        )
        job_items = fetch_all_pages(session, settings.search_url, token, job_query)
        for item in job_items:
            if not should_send_work_review_request_email(item, job_window_start):
                continue

            brief_number = get_field_value(item, JOB_BRIEF_NUMBER_FIELD_NAME)
            job_number = get_field_value(item, JOB_NUMBER_FIELD_NAME)
            job_name = get_field_value(item, JOB_NAME_FIELD_NAME) or job_number
            if not brief_number or not job_number or not job_name:
                logging.info(
                    "Skipping work review email because required job fields are missing: brief=%s, job=%s, name=%s",
                    brief_number or "<unknown>",
                    job_number or "<unknown>",
                    job_name or "<unknown>",
                )
                continue

            logging.info(
                "Sending work review email for job %s (brief %s, name %s)",
                job_number,
                brief_number,
                job_name,
            )
            send_work_review_request_email(brief_number, job_name, job_number)
        results.append(MonitoringResult(monitor=job_monitor, items=job_items))

        return results
