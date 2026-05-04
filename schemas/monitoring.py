from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleMonitor:
    label: str
    module_id: int
    last_modified_field_id: str


@dataclass(frozen=True)
class MonitoringResult:
    monitor: ModuleMonitor
    items: list[dict[str, Any]]
