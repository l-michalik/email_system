from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from config.constants import (
    BRIEF_EMAIL_SUBJECT,
    BRIEF_NUMBER_FIELD_NAME,
    CHANGE_REQUEST_UPDATED_EMAIL_SUBJECT,
    PAGE_SIZE,
    POLL_WINDOW_MINUTES,
)
from utils.mailer import send_email
from utils.email_templates import (
    EmailTemplateContent,
    build_email_html,
    build_email_text,
)


def cutoff_timestamp() -> str:
    cutoff = datetime.now(UTC) - timedelta(minutes=POLL_WINDOW_MINUTES)
    return cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_query(
    module_id: int,
    query_field_name: str,
    fields: dict[str, str],
    cutoff: str,
) -> str:
    selected_fields = ", ".join(fields.values())
    return (
        f"SELECT {selected_fields} FROM MODULE_{module_id} "
        f"WHERE {fields[query_field_name]} > '{cutoff}'"
    )


def fetch_page(
    session: requests.Session,
    url: str,
    token: str,
    query: str,
    start: int,
) -> list[dict[str, Any]]:
    response = session.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=query,
        params={
            "returnAllFields": False,
            "limit": PAGE_SIZE,
            "start": start,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["result"]


def fetch_all_pages(
    session: requests.Session,
    url: str,
    token: str,
    query: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    start = 1

    while True:
        page = fetch_page(session, url, token, query, start)
        items.extend(page)
        if len(page) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    return items


def get_field_value(item: dict[str, Any], field_name: str) -> str:
    field = next(field for field in item["fields"] if field["name"] == field_name)
    options = field["options"]
    return options[0]["value"] if options else ""


def parse_brief_created_date(value: str) -> datetime:
    return datetime.strptime(value, "%m/%d/%Y, %H:%M")


def _build_brief_creation_email_content(brief_number: str) -> EmailTemplateContent:
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


def build_brief_creation_email_text(brief_number: str) -> str:
    content = _build_brief_creation_email_content(brief_number)
    return build_email_text(content)


def build_brief_creation_email_html(brief_number: str) -> str:
    content = _build_brief_creation_email_content(brief_number)
    return build_email_html(content)


def _build_change_request_updated_email_content(brief_id: str) -> EmailTemplateContent:
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


def build_change_request_updated_email_text(brief_id: str) -> str:
    content = _build_change_request_updated_email_content(brief_id)
    return build_email_text(content)


def build_change_request_updated_email_html(brief_id: str) -> str:
    content = _build_change_request_updated_email_content(brief_id)
    return build_email_html(content)


def build_email_template_content(condition: str, brief_id: str) -> EmailTemplateContent:
    if condition == "brief_created":
        return _build_brief_creation_email_content(brief_id)
    if condition == "change_request_updated":
        return _build_change_request_updated_email_content(brief_id)
    raise ValueError(f"Unsupported email condition: {condition}")


def send_brief_creation_email(item: dict[str, Any]) -> None:
    brief_number = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
    body = build_brief_creation_email_text(brief_number)
    html_body = build_brief_creation_email_html(brief_number)
    send_email(BRIEF_EMAIL_SUBJECT, body, html_body=html_body)
