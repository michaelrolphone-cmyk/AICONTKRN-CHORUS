"""Continuity helpers for CHORUS runtime persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from chorus.expansion import materialize_expansion

ALLOWED_ROLES = {"user", "assistant", "system"}


@dataclass(frozen=True)
class InteractionRecord:
    ts: str
    role: str
    content: str

    def validate(self) -> None:
        if self.role not in ALLOWED_ROLES:
            raise ValueError(f"Unsupported role: {self.role}")
        if not self.content:
            raise ValueError("Interaction content must be non-empty")


def record_interaction(
    path: str | Path,
    *,
    role: str,
    content: str,
    clock: datetime | None = None,
) -> InteractionRecord:
    normalized_content = content
    if not content or not content.strip():
        normalized_content = "[empty]"
    if clock is None:
        clock = datetime.now(timezone.utc)
    record = InteractionRecord(ts=clock.isoformat(), role=role, content=normalized_content)
    record.validate()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        json.dump({"ts": record.ts, "role": record.role, "content": record.content}, handle)
        handle.write("\n")
    return record


def load_interactions(path: str | Path) -> list[InteractionRecord]:
    source = Path(path)
    if not source.exists():
        return []
    records: list[InteractionRecord] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        record = InteractionRecord(
            ts=payload["ts"],
            role=payload["role"],
            content=payload["content"],
        )
        record.validate()
        records.append(record)
    return records


def bootstrap_continuity(
    desires_path: str | Path,
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    session_log_path: str | Path,
    source: str,
    clock: datetime | None = None,
) -> tuple[InteractionRecord, str]:
    ledger, snapshot = materialize_expansion(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        source=source,
        clock=clock,
    )
    record = record_interaction(
        session_log_path,
        role="system",
        content=f"Bootstrap continuity: {len(ledger.entries)} desires materialized.",
        clock=clock,
    )
    return record, snapshot.timestamp
