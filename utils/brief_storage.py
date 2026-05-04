from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from config.constants import CHATBOT_CREATED_BY_OPTION_ID
from utils.monitoring import get_field_value


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "briefs.sqlite3"
logger = logging.getLogger(__name__)
_is_table_created = False
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
    field = next((field for field in item["fields"] if field["name"] == field_name), None)
    if field is None:
        return []

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


def _notification_event_key(
    event_type: str,
    entity_id: str,
    event_timestamp: str | None = None,
) -> str:
    if event_timestamp:
        return f"{event_type}:{entity_id}:{event_timestamp}"
    return f"{event_type}:{entity_id}"


def _load_brief_row(brief_number: str) -> dict[str, Any] | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
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


def _load_job_row(job_number: str) -> dict[str, Any] | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        row = connection.execute(
            """
            SELECT
                job_number,
                brief_number,
                last_modified_date,
                status,
                assets,
                output_files_link
            FROM chatbot_jobs
            WHERE job_number = ? LIMIT 1
            """,
            (job_number,),
        ).fetchone()

    if row is None:
        return None

    return {
        "job_number": row[0],
        "brief_number": row[1],
        "last_modified_date": row[2],
        "status": row[3],
        "assets": row[4],
        "output_files_link": row[5],
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
        _get_json_field_value(item, BRIEF_DOCUMENT_FIELD_NAME),
        _get_json_field_value(item, SUPPORTING_DOCUMENTS_FIELD_NAME),
        _get_json_field_value(item, MEDIA_PLANS_FIELD_NAME),
    )


def _job_values_from_item(item: dict[str, Any]) -> tuple[str | None, ...]:
    return (
        get_field_value(item, "Job Number"),
        get_field_value(item, "Brief Number"),
        get_field_value(item, "Last Modified Date"),
        get_field_value(item, "Status"),
        get_field_value(item, "Assets"),
        get_field_value(item, "Link to Output Files (Client)"),
    )


def _should_send_update(previous: dict[str, Any], current_item: dict[str, Any]) -> bool:
    current_brief_description = get_field_value(current_item, BRIEF_DESCRIPTION_FIELD_NAME)
    if previous[BRIEF_DESCRIPTION_FIELD_NAME] != current_brief_description:
        logger.info("Brief %s update detected: description changed", previous["brief_number"])
        return True

    current_brief_sla = get_field_value(current_item, BRIEF_SLA_FIELD_NAME)
    if (
        (previous[BRIEF_SLA_FIELD_NAME] or "").strip().lower() == "standard sla"
        and (current_brief_sla or "").strip().lower() == "rush sla"
    ):
        logger.info("Brief %s update detected: SLA changed to rush", previous["brief_number"])
        return True

    current_work_type = _get_field_values(current_item, WORK_TYPE_FIELD_NAME)
    if set(previous[WORK_TYPE_FIELD_NAME]) != set(current_work_type):
        logger.info("Brief %s update detected: work type changed", previous["brief_number"])
        return True

    previous_client_review_deadline = _parse_date(previous[CLIENT_REVIEW_DEADLINE_FIELD_NAME])
    current_client_review_deadline = _parse_date(
        get_field_value(current_item, CLIENT_REVIEW_DEADLINE_FIELD_NAME)
    )
    if (
        previous_client_review_deadline
        and current_client_review_deadline
        and current_client_review_deadline < previous_client_review_deadline
    ):
        logger.info(
            "Brief %s update detected: client review deadline moved earlier",
            previous["brief_number"],
        )
        return True

    previous_delivery_deadline = _parse_date(previous[DELIVERY_DEADLINE_FIELD_NAME])
    current_delivery_deadline = _parse_date(get_field_value(current_item, DELIVERY_DEADLINE_FIELD_NAME))
    if (
        previous_delivery_deadline
        and current_delivery_deadline
        and current_delivery_deadline < previous_delivery_deadline
    ):
        logger.info(
            "Brief %s update detected: delivery deadline moved earlier",
            previous["brief_number"],
        )
        return True

    previous_budget = _parse_decimal(previous[BUDGET_FIELD_NAME])
    current_budget = _parse_decimal(get_field_value(current_item, BUDGET_FIELD_NAME))
    if previous_budget is not None and current_budget is not None and current_budget < previous_budget:
        logger.info("Brief %s update detected: budget decreased", previous["brief_number"])
        return True

    for field_name in (
        BRIEF_DOCUMENT_FIELD_NAME,
        SUPPORTING_DOCUMENTS_FIELD_NAME,
        MEDIA_PLANS_FIELD_NAME,
    ):
        previous_files = set(previous[field_name])
        current_files = set(_get_field_values(current_item, field_name))
        if previous_files - current_files:
            logger.info(
                "Brief %s update detected: files removed from %s",
                previous["brief_number"],
                field_name,
            )
            return True

    logger.info("Brief %s has no notification-worthy update", previous["brief_number"])
    return False


def _create_table(connection: sqlite3.Connection) -> None:
    logger.info("Ensuring chatbot storage schema exists at %s", DB_PATH)
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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            monitor_label TEXT PRIMARY KEY,
            last_successful_sync TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_notifications (
            event_key TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            event_timestamp TEXT,
            sent_at TEXT NOT NULL
        )
        """
    )


def _ensure_table_created(connection: sqlite3.Connection) -> None:
    global _is_table_created

    if _is_table_created:
        return

    _create_table(connection)
    _is_table_created = True


def brief_exists(brief_number: str) -> bool:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        row = connection.execute(
            "SELECT 1 FROM chatbot_briefs WHERE brief_number = ? LIMIT 1",
            (brief_number,),
        ).fetchone()
    exists = row is not None
    logger.info("Brief %s exists in storage: %s", brief_number, exists)
    return exists


def store_chatbot_brief(item: dict[str, Any]) -> None:
    brief_values = _brief_values_from_item(item)
    logger.info("Storing chatbot brief %s", brief_values[0])
    create_email_sent = int(bool(brief_values[0]) and is_create_email_sent(brief_values[0]))

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
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
            brief_values + (create_email_sent,),
        )
        connection.commit()
    logger.info("Stored chatbot brief %s", brief_values[0])


def save_chatbot_brief(item: dict[str, Any]) -> None:
    brief_number = get_field_value(item, "Brief Number")
    if not brief_number:
        logger.info("Skipping chatbot brief save because Brief Number is missing")
        return

    if brief_exists(brief_number):
        update_chatbot_brief(item)
        return

    store_chatbot_brief(item)


def get_chatbot_brief(brief_number: str) -> dict[str, Any] | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = _load_brief_row(brief_number)
    logger.info("Loaded chatbot brief %s: %s", brief_number, row is not None)
    return row


def update_chatbot_brief(item: dict[str, Any]) -> None:
    brief_number = get_field_value(item, "Brief Number")
    if not brief_number:
        logger.info("Skipping brief update because Brief Number is missing")
        return

    existing_brief = _load_brief_row(brief_number)
    if existing_brief is None:
        logger.info("Skipping brief update because brief %s is not stored", brief_number)
        return

    brief_values = _brief_values_from_item(item)
    logger.info("Updating chatbot brief %s", brief_number)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
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
            brief_values[1:] + (existing_brief["IsCreateEmailSent"], brief_number),
        )
        connection.commit()
    logger.info("Updated chatbot brief %s", brief_number)


def should_send_change_request_updated_email(item: dict[str, Any]) -> bool:
    brief_number = get_field_value(item, "Brief Number")
    if not brief_number:
        logger.info("Skipping change request update check because Brief Number is missing")
        return False

    previous_brief = _load_brief_row(brief_number)
    if previous_brief is None:
        logger.info(
            "Skipping change request update check because brief %s is not stored",
            brief_number,
        )
        return False

    return _should_send_update(previous_brief, item)


def job_exists(job_number: str) -> bool:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        row = connection.execute(
            "SELECT 1 FROM chatbot_jobs WHERE job_number = ? LIMIT 1",
            (job_number,),
        ).fetchone()
    exists = row is not None
    logger.info("Job %s exists in storage: %s", job_number, exists)
    return exists


def store_chatbot_job(item: dict[str, Any]) -> None:
    job_values = _job_values_from_item(item)
    logger.info("Storing chatbot job %s for brief %s", job_values[0], job_values[1])

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
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
            job_values,
        )
        connection.commit()
    logger.info("Stored chatbot job %s", job_values[0])


def save_chatbot_job(item: dict[str, Any]) -> None:
    job_number = get_field_value(item, "Job Number")
    if not job_number:
        logger.info("Skipping chatbot job save because Job Number is missing")
        return

    if job_exists(job_number):
        update_chatbot_job(item)
        return

    store_chatbot_job(item)


def get_chatbot_job(job_number: str) -> dict[str, Any] | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = _load_job_row(job_number)
    logger.info("Loaded chatbot job %s: %s", job_number, row is not None)
    return row


def update_chatbot_job(item: dict[str, Any]) -> None:
    job_number = get_field_value(item, "Job Number")
    if not job_number:
        logger.info("Skipping job update because Job Number is missing")
        return

    existing_job = _load_job_row(job_number)
    if existing_job is None:
        logger.info("Skipping job update because job %s is not stored", job_number)
        return

    job_values = _job_values_from_item(item)
    logger.info("Updating chatbot job %s", job_number)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        connection.execute(
            """
            UPDATE chatbot_jobs
            SET
                brief_number = ?,
                last_modified_date = ?,
                status = ?,
                assets = ?,
                output_files_link = ?
            WHERE job_number = ?
            """,
            job_values[1:] + (job_number,),
        )
        connection.commit()
    logger.info("Updated chatbot job %s", job_number)


def get_sync_checkpoint(monitor_label: str) -> str | None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        row = connection.execute(
            """
            SELECT last_successful_sync
            FROM sync_state
            WHERE monitor_label = ? LIMIT 1
            """,
            (monitor_label,),
        ).fetchone()
    checkpoint = row[0] if row else None
    logger.info("Loaded sync checkpoint for %s: %s", monitor_label, checkpoint)
    return checkpoint


def set_sync_checkpoint(monitor_label: str, timestamp: str) -> None:
    logger.info("Saving sync checkpoint for %s: %s", monitor_label, timestamp)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        connection.execute(
            """
            INSERT INTO sync_state (monitor_label, last_successful_sync)
            VALUES (?, ?)
            ON CONFLICT(monitor_label)
            DO UPDATE SET last_successful_sync = excluded.last_successful_sync
            """,
            (monitor_label, timestamp),
        )
        connection.commit()


def has_sent_notification(
    event_type: str,
    entity_id: str,
    event_timestamp: str | None = None,
) -> bool:
    event_key = _notification_event_key(event_type, entity_id, event_timestamp)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        row = connection.execute(
            "SELECT 1 FROM sent_notifications WHERE event_key = ? LIMIT 1",
            (event_key,),
        ).fetchone()
    sent = row is not None
    logger.info("Notification sent for %s: %s", event_key, sent)
    return sent


def record_notification(
    event_type: str,
    entity_id: str,
    event_timestamp: str | None = None,
) -> None:
    event_key = _notification_event_key(event_type, entity_id, event_timestamp)
    sent_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    logger.info("Recording notification %s at %s", event_key, sent_at)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        connection.execute(
            """
            INSERT OR IGNORE INTO sent_notifications (
                event_key,
                event_type,
                entity_id,
                event_timestamp,
                sent_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_key, event_type, entity_id, event_timestamp, sent_at),
        )
        connection.commit()


def is_chatbot_brief(brief_number: str) -> bool:
    brief = _load_brief_row(brief_number)
    if brief is None:
        logger.info("Chatbot brief check failed for %s: brief not found", brief_number)
        return False

    is_chatbot_created = brief["created_by_chatbot"] == CHATBOT_CREATED_BY_OPTION_ID
    logger.info("Chatbot brief check for %s: %s", brief_number, is_chatbot_created)
    return is_chatbot_created


def is_create_email_sent(brief_number: str) -> bool:
    return has_sent_notification("brief_created", brief_number)


def mark_create_email_sent(brief_number: str) -> None:
    logger.info("Marking create email sent for brief %s", brief_number)
    record_notification("brief_created", brief_number)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_table_created(connection)
        connection.execute(
            'UPDATE chatbot_briefs SET "IsCreateEmailSent" = 1 WHERE brief_number = ?',
            (brief_number,),
        )
        connection.commit()
    logger.info("Marked create email sent for brief %s", brief_number)
