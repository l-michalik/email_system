from __future__ import annotations

from schemas.monitoring import ModuleMonitor

POLL_WINDOW_MINUTES = 5
PAGE_SIZE = 100
BRIEF_PAGE_SIZE = 250

BRIEF_FIELDS: dict[str, str] = {
    "Created Date": "173",
    "Created By ChatBot": "4747",
    "Last Modified Date": "3100",
    "Brief Number": "4660",
}

JOB_FIELDS: dict[str, str] = {
    "Last Modified Date": "1285",
}

MONITORED_MODULES: tuple[ModuleMonitor, ...] = (
    ModuleMonitor("brief", 3, "Last Modified Date", BRIEF_FIELDS),
    ModuleMonitor("job", 14, "Last Modified Date", JOB_FIELDS),
)
