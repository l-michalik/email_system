from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from config.constants import POLL_WINDOW_MINUTES

logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _crm_field(field_id: str) -> str:
    return f"FD_{field_id}"


def cutoff_timestamp() -> str:
    cutoff = datetime.now(UTC) - timedelta(minutes=POLL_WINDOW_MINUTES)
    timestamp = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
    return timestamp


def build_query(
    module_id: int,
    query_field_name: str,
    fields: dict[str, str],
    cutoff: str,
    select_all_fields: bool = False,
) -> str:
    selected_fields = "*"
    if not select_all_fields:
        selected_fields = ", ".join(_crm_field(field_id) for field_id in fields.values())
    query = (
        f"SELECT {selected_fields} FROM MODULE_{module_id} "
        f"WHERE {_crm_field(fields[query_field_name])} > '{cutoff}'"
    )
    return query


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


def get_field_email(item: dict[str, Any], field_name: str) -> str | None:
    field = next((field for field in item["fields"] if field["name"] == field_name), None)
    if field is None:
        return None

    for option in reversed(field["options"]):
        for key in ("email", "value", "text", "name", "label"):
            candidate = option.get(key)
            if not isinstance(candidate, str):
                continue
            match = EMAIL_PATTERN.search(candidate)
            if match:
                return match.group(0)

    return None


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
