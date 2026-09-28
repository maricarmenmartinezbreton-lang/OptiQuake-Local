"""Stable plugin contract for OptiQuake Local.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only
"""
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Protocol

PLUGIN_API_VERSION = "1"

@dataclass(frozen=True)
class VibrationEvent:
    t: float
    score: float
    baseline: float
    robust_z: float
    source: str = "optical"
    event: str = "vibration"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class OptiQuakePlugin(Protocol):
    name: str
    version: str
    api_version: str

    def on_start(self, context: Mapping[str, Any]) -> None: ...
    def on_event(self, event: VibrationEvent) -> None: ...
    def on_stop(self) -> None: ...
