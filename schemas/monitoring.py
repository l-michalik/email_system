from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleMonitor:
    label: str
    module_id: int
    query_field_name: str
    fields: dict[str, str]
    select_all_fields: bool = False


@dataclass(frozen=True)
class MonitoringResult:
    monitor: ModuleMonitor
    items: list[dict[str, Any]]
