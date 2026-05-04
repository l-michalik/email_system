from __future__ import annotations

from schemas.monitoring import ModuleMonitor

POLL_WINDOW_MINUTES = 5
PAGE_SIZE = 100
BRIEF_CREATED_BY_CHATBOT_VALUE = "Yes"
BRIEF_EMAIL_SUBJECT = "Your Brief Has Been Created – Please Save the Brief ID"
CHANGE_REQUEST_UPDATED_EMAIL_SUBJECT = "Your change request has been successfully updated"
BRIEF_CREATED_DATE_FIELD_NAME = "Created Date"
BRIEF_CREATED_BY_CHATBOT_FIELD_NAME = "Created By ChatBot"
BRIEF_NUMBER_FIELD_NAME = "Brief Number"

BRIEF_FIELDS: dict[str, str] = {
    "created_date": "fd_173",
    "created_by_chatbot": "fd_4747",
    "brief_number": "fd_4660",
}

JOB_FIELDS: dict[str, str] = {
    "last_modified": "fd_1285",
}

MONITORED_MODULES: tuple[ModuleMonitor, ...] = (
    ModuleMonitor("brief", 3, "created_date", BRIEF_FIELDS),
    ModuleMonitor("job", 14, "last_modified", JOB_FIELDS),
)
