from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Any

from utils.monitoring import get_field_value


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "briefs.sqlite3"
BRIEF_DESCRIPTION_FIELD_NAME = "Brief Description"
BRIEF_SLA_FIELD_NAME = "Brief SLA"
WORK_TYPE_FIELD_NAME = "Work Type"
CLIENT_REVIEW_DEADLINE_FIELD_NAME = "Client Review Deadline"
DELIVERY_DEADLINE_FIELD_NAME = "Delivery Deadline"
BUDGET_FIELD_NAME = "Budget"
BRIEF_DOCUMENT_FIELD_NAME = "Brief Document"
SUPPORTING_DOCUMENTS_FIELD_NAME = "Supporting Documents"
MEDIA_PLANS_FIELD_NAME = "Media Plans"


def _get_option_value(option: dict[str, Any]) -> str | None:
    return next(
        (option[key] for key in ("value", "text", "name", "label") if key in option),
        None,
    )


def _get_field_values(item: dict[str, Any], field_name: str) -> list[str]:
    field = next(field for field in item["fields"] if field["name"] == field_name)
    options = field["options"]
    if not options:
        return []
    return [value for option in options if (value := _get_option_value(option))]


def _get_json_field_value(item: dict[str, Any], field_name: str) -> str:
    return json.dumps(_get_field_values(item, field_name), ensure_ascii=False)


def _parse_json_field_value(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    if isinstance(parsed_value, list):
        return [item for item in parsed_value if isinstance(item, str)]
    if isinstance(parsed_value, str):
        return [parsed_value]
    return []


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for format_string in ("%m/%d/%Y, %H:%M", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, format_string)
        except ValueError:
            continue
    return None


def _parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned_value = value.replace(",", "").replace("$", "").strip()
    try:
        return Decimal(cleaned_value)
    except InvalidOperation:
        return None


def _load_brief_row(brief_number: str) -> dict[str, Any] | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        row = connection.execute(
            """
            SELECT
                brief_number,
                created_by_chatbot,
                "Created Date",
                "Last Modified Date",
                "Brief Description",
                "Brief SLA",
                "Work Type",
                "Client Review Deadline",
                "Delivery Deadline",
                "Budget",
                "Brief Document",
                "Supporting Documents",
                "Media Plans",
                "IsCreateEmailSent"
            FROM chatbot_briefs
            WHERE brief_number = ? LIMIT 1
            """,
            (brief_number,),
        ).fetchone()

    if row is None:
        return None

    return {
        "brief_number": row[0],
        "created_by_chatbot": row[1],
        "Created Date": row[2],
        "Last Modified Date": row[3],
        BRIEF_DESCRIPTION_FIELD_NAME: row[4],
        BRIEF_SLA_FIELD_NAME: row[5],
        WORK_TYPE_FIELD_NAME: _parse_json_field_value(row[6]),
        CLIENT_REVIEW_DEADLINE_FIELD_NAME: row[7],
        DELIVERY_DEADLINE_FIELD_NAME: row[8],
        BUDGET_FIELD_NAME: row[9],
        BRIEF_DOCUMENT_FIELD_NAME: _parse_json_field_value(row[10]),
        SUPPORTING_DOCUMENTS_FIELD_NAME: _parse_json_field_value(row[11]),
        MEDIA_PLANS_FIELD_NAME: _parse_json_field_value(row[12]),
        "IsCreateEmailSent": bool(row[13]),
    }


def _brief_values_from_item(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        get_field_value(item, "Brief Number"),
        get_field_value(item, "Created By ChatBot"),
        get_field_value(item, "Created Date"),
        get_field_value(item, "Last Modified Date"),
        get_field_value(item, "Brief Description"),
        get_field_value(item, "Brief SLA"),
        _get_json_field_value(item, WORK_TYPE_FIELD_NAME),
        get_field_value(item, "Client Review Deadline"),
        get_field_value(item, "Delivery Deadline"),
        get_field_value(item, "Budget"),
        _get_json_field_value(item, "Brief Document"),
        _get_json_field_value(item, "Supporting Documents"),
        _get_json_field_value(item, "Media Plans"),
    )


def _should_send_update(previous: dict[str, Any], current_item: dict[str, Any]) -> bool:
    current_brief_description = get_field_value(current_item, "Brief Description")
    if previous["Brief Description"] != current_brief_description:
        return True

    current_brief_sla = get_field_value(current_item, "Brief SLA")
    if (
        (previous["Brief SLA"] or "").strip().lower() == "standard sla"
        and (current_brief_sla or "").strip().lower() == "rush sla"
    ):
        return True

    current_work_type = _get_field_values(current_item, WORK_TYPE_FIELD_NAME)
    if set(previous[WORK_TYPE_FIELD_NAME]) != set(current_work_type):
        return True

    previous_client_review_deadline = _parse_date(previous["Client Review Deadline"])
    current_client_review_deadline = _parse_date(
        get_field_value(current_item, "Client Review Deadline")
    )
    if (
        previous_client_review_deadline
        and current_client_review_deadline
        and current_client_review_deadline < previous_client_review_deadline
    ):
        return True

    previous_delivery_deadline = _parse_date(previous["Delivery Deadline"])
    current_delivery_deadline = _parse_date(
        get_field_value(current_item, "Delivery Deadline")
    )
    if (
        previous_delivery_deadline
        and current_delivery_deadline
        and current_delivery_deadline < previous_delivery_deadline
    ):
        return True

    previous_budget = _parse_decimal(previous["Budget"])
    current_budget = _parse_decimal(get_field_value(current_item, "Budget"))
    if previous_budget is not None and current_budget is not None and current_budget < previous_budget:
        return True

    for field_name in (
        "Brief Document",
        "Supporting Documents",
        "Media Plans",
    ):
        previous_files = set(previous[field_name])
        current_files = set(_get_field_values(current_item, field_name))
        if previous_files - current_files:
            return True

    return False


def _create_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chatbot_briefs (
            brief_number TEXT PRIMARY KEY,
            created_by_chatbot TEXT NOT NULL,
            "Created Date" TEXT NOT NULL,
            "Last Modified Date" TEXT NOT NULL,
            "Brief Description" TEXT,
            "Brief SLA" TEXT,
            "Work Type" TEXT,
            "Client Review Deadline" TEXT,
            "Delivery Deadline" TEXT,
            "Budget" TEXT,
            "Brief Document" TEXT,
            "Supporting Documents" TEXT,
            "Media Plans" TEXT,
            "IsCreateEmailSent" INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chatbot_jobs (
            job_number TEXT PRIMARY KEY,
            brief_number TEXT NOT NULL,
            last_modified_date TEXT,
            status TEXT,
            assets TEXT,
            output_files_link TEXT
        )
        """
    )


def brief_exists(brief_number: str) -> bool:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        row = connection.execute(
            "SELECT 1 FROM chatbot_briefs WHERE brief_number = ? LIMIT 1",
            (brief_number,),
        ).fetchone()
    return row is not None


def store_chatbot_brief(item: dict[str, Any]) -> None:
    brief_values = _brief_values_from_item(item)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        connection.execute(
            """
            INSERT INTO chatbot_briefs (
                brief_number,
                created_by_chatbot,
                "Created Date",
                "Last Modified Date",
                "Brief Description",
                "Brief SLA",
                "Work Type",
                "Client Review Deadline",
                "Delivery Deadline",
                "Budget",
                "Brief Document",
                "Supporting Documents",
                "Media Plans",
                "IsCreateEmailSent"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            brief_values + (0,),
        )
        connection.commit()


def get_chatbot_brief(brief_number: str) -> dict[str, Any] | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _load_brief_row(brief_number)


def update_chatbot_brief(item: dict[str, Any]) -> None:
    brief_number = get_field_value(item, "Brief Number")
    if not brief_number:
        return

    existing_brief = _load_brief_row(brief_number)
    if existing_brief is None:
        return

    brief_values = _brief_values_from_item(item)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        connection.execute(
            """
            UPDATE chatbot_briefs
            SET
                created_by_chatbot = ?,
                "Created Date" = ?,
                "Last Modified Date" = ?,
                "Brief Description" = ?,
                "Brief SLA" = ?,
                "Work Type" = ?,
                "Client Review Deadline" = ?,
                "Delivery Deadline" = ?,
                "Budget" = ?,
                "Brief Document" = ?,
                "Supporting Documents" = ?,
                "Media Plans" = ?,
                "IsCreateEmailSent" = ?
            WHERE brief_number = ?
            """,
            brief_values[1:]
            + (
                existing_brief["IsCreateEmailSent"],
                brief_number,
            ),
        )
        connection.commit()


def should_send_change_request_updated_email(item: dict[str, Any]) -> bool:
    brief_number = get_field_value(item, "Brief Number")
    if not brief_number:
        return False

    previous_brief = _load_brief_row(brief_number)
    if previous_brief is None:
        return False

    return _should_send_update(previous_brief, item)


def job_exists(job_number: str) -> bool:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        row = connection.execute(
            "SELECT 1 FROM chatbot_jobs WHERE job_number = ? LIMIT 1",
            (job_number,),
        ).fetchone()
    return row is not None


def store_chatbot_job(item: dict[str, Any]) -> None:
    job_number = get_field_value(item, "Job Number")
    brief_number = get_field_value(item, "Brief Number")
    last_modified_date = get_field_value(item, "Last Modified Date")
    status = get_field_value(item, "Status")
    assets = get_field_value(item, "Assets")
    output_files_link = get_field_value(item, "Link to Output Files (Client)")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        connection.execute(
            """
            INSERT INTO chatbot_jobs (
                job_number,
                brief_number,
                last_modified_date,
                status,
                assets,
                output_files_link
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_number,
                brief_number,
                last_modified_date,
                status,
                assets,
                output_files_link,
            ),
        )
        connection.commit()


def is_create_email_sent(brief_number: str) -> bool:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        row = connection.execute(
            'SELECT "IsCreateEmailSent" FROM chatbot_briefs WHERE brief_number = ? LIMIT 1',
            (brief_number,),
        ).fetchone()
    return bool(row and row[0])


def mark_create_email_sent(brief_number: str) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _create_table(connection)
        connection.execute(
            'UPDATE chatbot_briefs SET "IsCreateEmailSent" = 1 WHERE brief_number = ?',
            (brief_number,),
        )
        connection.commit()
