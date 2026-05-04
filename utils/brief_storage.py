from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from config.constants import (
    BRIEF_CREATED_BY_CHATBOT_FIELD_NAME,
    BRIEF_CREATED_DATE_FIELD_NAME,
    BRIEF_LAST_MODIFIED_DATE_FIELD_NAME,
    BRIEF_NUMBER_FIELD_NAME,
)
from utils.monitoring import get_field_value


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "briefs.sqlite3"


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
            "Media Plans" TEXT
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
    brief_number = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
    created_by_chatbot = get_field_value(item, BRIEF_CREATED_BY_CHATBOT_FIELD_NAME)
    created_date = get_field_value(item, BRIEF_CREATED_DATE_FIELD_NAME)
    last_modified_date = get_field_value(item, BRIEF_LAST_MODIFIED_DATE_FIELD_NAME)
    brief_description = get_field_value(item, "Brief Description")
    brief_sla = get_field_value(item, "Brief SLA")
    work_type = get_field_value(item, "Work Type")
    client_review_deadline = get_field_value(item, "Client Review Deadline")
    delivery_deadline = get_field_value(item, "Delivery Deadline")
    budget = get_field_value(item, "Budget")
    brief_document = get_field_value(item, "Brief Document")
    supporting_documents = get_field_value(item, "Supporting Documents")
    media_plans = get_field_value(item, "Media Plans")

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
                "Media Plans"
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brief_number,
                created_by_chatbot,
                created_date,
                last_modified_date,
                brief_description,
                brief_sla,
                work_type,
                client_review_deadline,
                delivery_deadline,
                budget,
                brief_document,
                supporting_documents,
                media_plans,
            ),
        )
        connection.commit()
