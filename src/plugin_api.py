"""Stable plugin contract for OptiQuake Local.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only
"""
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Optional, Protocol

PLUGIN_API_VERSION = "1"

@dataclass(frozen=True)
class VibrationEvent:
    t: float
    score: float
    baseline: float
    robust_z: float
    source: str = "optical"
    event: str = "vibration"
    # Optional evidence (unreleased; omitted from to_dict() when unset).
    coverage: Optional[float] = None   # fraction of image cells that moved
    shift_px: Optional[float] = None   # global image shift between frames
    audio_z: Optional[float] = None    # low-frequency microphone robust z

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

class OptiQuakePlugin(Protocol):
    name: str
    version: str
    api_version: str

    def on_start(self, context: Mapping[str, Any]) -> None: ...
    def on_event(self, event: VibrationEvent) -> None: ...
    def on_stop(self) -> None: ...
