from __future__ import annotations

from schemas.monitoring import ModuleMonitor

POLL_WINDOW_MINUTES = 5
PAGE_SIZE = 100

MONITORED_MODULES: tuple[ModuleMonitor, ...] = (
    ModuleMonitor("brief", 3, "fd_3100"),
    ModuleMonitor("job", 14, "fd_1285"),
)
