from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests

from config.constants import (
    BRIEF_CREATED_BY_CHATBOT_FIELD_NAME,
    BRIEF_CREATED_BY_CHATBOT_VALUE,
    BRIEF_CREATED_DATE_FIELD_NAME,
    BRIEF_EMAIL_SUBJECT,
    BRIEF_NUMBER_FIELD_NAME,
    CHANGE_REQUEST_UPDATED_EMAIL_SUBJECT,
    MONITORED_MODULES,
    POLL_WINDOW_MINUTES,
    WORK_REVIEW_REQUEST_EMAIL_SUBJECT,
)
from config.settings import AppSettings
from schemas.monitoring import MonitoringResult
from utils import get_token
from utils.email_templates import EmailTemplateContent, build_email_html, build_email_text
from utils.mailer import send_email
from utils.monitoring import (
    build_query,
    cutoff_timestamp,
    fetch_all_pages,
    get_field_value,
    parse_brief_created_date,
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
                    brief_id = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
                    send_brief_creation_email(brief_id)
                    created_at = parse_brief_created_date(
                        get_field_value(item, BRIEF_CREATED_DATE_FIELD_NAME)
                    )
                    if created_at < created_cutoff:
                        continue

            results.append(MonitoringResult(monitor=monitor, items=items))

        return results
