"""State snapshot exports for CHORUS continuity hardening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class StateSnapshot:
    timestamp: str
    data: dict[str, Any]

    @classmethod
    def now(cls, data: dict[str, Any], clock: datetime | None = None) -> "StateSnapshot":
        if clock is None:
            clock = datetime.now(timezone.utc)
        return cls(timestamp=clock.isoformat(), data=data)


def export_state(path: str | Path, snapshot: StateSnapshot) -> Path:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": snapshot.timestamp,
        "state": snapshot.data,
    }
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return state_path
