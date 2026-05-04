from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from config.constants import PAGE_SIZE, POLL_WINDOW_MINUTES


def _crm_field(field_id: str) -> str:
    return f"FD_{field_id}"


def cutoff_timestamp() -> str:
    cutoff = datetime.now(UTC) - timedelta(minutes=POLL_WINDOW_MINUTES)
    return cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_query(
    module_id: int,
    query_field_name: str,
    fields: dict[str, str],
    cutoff: str,
) -> str:
    selected_fields = ", ".join(_crm_field(field_id) for field_id in fields.values())
    return (
        f"SELECT {selected_fields} FROM MODULE_{module_id} "
        f"WHERE {_crm_field(fields[query_field_name])} > '{cutoff}'"
    )


def fetch_page(
    session: requests.Session,
    url: str,
    token: str,
    query: str,
    start: int,
    page_size: int = PAGE_SIZE,
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
            "limit": page_size,
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
    page_size: int = PAGE_SIZE,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    start = 1

    while True:
        page = fetch_page(session, url, token, query, start, page_size)
        items.extend(page)
        if len(page) < page_size:
            break
        start += page_size

    return items


def get_field_value(item: dict[str, Any], field_name: str) -> str | None:
    field = next((field for field in item["fields"] if field["name"] == field_name), None)
    if field is None:
        return None

    options = field["options"]
    if not options:
        return None
    # The API returns option history in order; the current value is the last entry.
    option = options[-1]
    return next(
        (option[key] for key in ("value", "text", "name", "label") if key in option),
        None,
    )


def parse_brief_last_modified_date(value: str) -> datetime:
    candidates: list[datetime] = []
    for format_string in ("%m/%d/%Y, %H:%M", "%d/%m/%Y, %H:%M"):
        try:
            candidates.append(datetime.strptime(value, format_string))
        except ValueError:
            continue

    if not candidates:
        raise ValueError(f"Unsupported date format: {value}")
    if len(candidates) == 1:
        return candidates[0]

    now = datetime.now()
    return min(candidates, key=lambda candidate: abs(candidate - now))
