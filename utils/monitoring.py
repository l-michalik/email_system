from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

from config.constants import PAGE_SIZE, POLL_WINDOW_MINUTES


def cutoff_timestamp() -> str:
    cutoff = datetime.now(UTC) - timedelta(minutes=POLL_WINDOW_MINUTES)
    return cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_query(module_id: int, field_id: str, cutoff: str) -> str:
    return f"SELECT {field_id} FROM MODULE_{module_id} WHERE {field_id} > '{cutoff}'"


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
