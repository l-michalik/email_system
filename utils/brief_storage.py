from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config.constants import (
    BRIEF_CREATED_BY_CHATBOT_FIELD_NAME,
    BRIEF_CREATED_DATE_FIELD_NAME,
    BRIEF_NUMBER_FIELD_NAME,
)
from utils.monitoring import get_field_value


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "briefs.sqlite3"


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chatbot_briefs (
            brief_number TEXT PRIMARY KEY,
            created_by_chatbot TEXT NOT NULL,
            created_date TEXT NOT NULL,
            raw_item TEXT NOT NULL,
            stored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def store_chatbot_brief(item: dict[str, Any]) -> None:
    brief_number = get_field_value(item, BRIEF_NUMBER_FIELD_NAME)
    created_by_chatbot = get_field_value(item, BRIEF_CREATED_BY_CHATBOT_FIELD_NAME)
    created_date = get_field_value(item, BRIEF_CREATED_DATE_FIELD_NAME)
    payload = json.dumps(item, ensure_ascii=False, default=str)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        _ensure_schema(connection)
        connection.execute(
            """
            INSERT INTO chatbot_briefs (
                brief_number,
                created_by_chatbot,
                created_date,
                raw_item,
                stored_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(brief_number) DO UPDATE SET
                created_by_chatbot = excluded.created_by_chatbot,
                created_date = excluded.created_date,
                raw_item = excluded.raw_item,
                stored_at = CURRENT_TIMESTAMP
            """,
            (
                brief_number,
                created_by_chatbot,
                created_date,
                payload,
            ),
        )
        connection.commit()
