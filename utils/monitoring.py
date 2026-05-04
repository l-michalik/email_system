from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from config.constants import (
    BRIEF_CREATED_DATE_FIELD_NAME,
    BRIEF_EMAIL_SUBJECT,
    PAGE_SIZE,
    POLL_WINDOW_MINUTES,
)
from utils.mailer import send_email


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


def send_brief_creation_email(item: dict[str, Any]) -> None:
    created_date = get_field_value(item, BRIEF_CREATED_DATE_FIELD_NAME)
    body = (
        "A new brief was created by ChatBot.\n\n"
        f"Created date: {created_date}\n"
    )
    send_email(BRIEF_EMAIL_SUBJECT, body)
