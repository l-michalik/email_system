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
    "Main Client Contact": "4713",
}

JOB_FIELDS: dict[str, str] = {
    "Job Number": "471",
    "Job Name": "975",
    "Brief Number": "1291",
    "Last Modified Date": "1285",
    "Status": "316",
    "Assets": "229",
    "Link to Output Files (Client)": "4406",
    "Main Client Contact": "4472",
}

MONITORED_MODULES: tuple[ModuleMonitor, ...] = (
    ModuleMonitor(
        "brief",
        3,
        "Last Modified Date",
        BRIEF_FIELDS,
        select_all_fields=True,
        filter_condition=f"FD_4747 = {'6366'}",
    ),
    ModuleMonitor("job", 14, "Last Modified Date", JOB_FIELDS),
)
