"""Expansion tooling for CHORUS desire parsing and ledger/state updates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from chorus.ledger import Ledger, LedgerEntry
from chorus.state import StateSnapshot, export_state


@dataclass(frozen=True)
class Desire:
    index: int
    title: str
    body: str


def parse_desires(text: str) -> list[Desire]:
    desires: list[Desire] = []
    current: dict[str, object] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current and current["body_lines"]:
                current["body_lines"].append("")
            continue
        match = re.match(r"^(\d+)[\).]\s+(.*)$", stripped)
        if match:
            if current:
                desires.append(_finalize_desire(current))
            current = {
                "index": int(match.group(1)),
                "title": match.group(2).strip(),
                "body_lines": [],
            }
            continue
        if current:
            current["body_lines"].append(stripped)
    if current:
        desires.append(_finalize_desire(current))
    return desires


def build_expansion_ledger(
    desires: list[Desire],
    *,
    source: str,
    clock: datetime | None = None,
) -> Ledger:
    if clock is None:
        clock = datetime.now(timezone.utc)
    ledger = Ledger()
    for desire in desires:
        entry = LedgerEntry.now(
            type="PROJECT",
            topic=desire.title,
            content=desire.body or "Expansion desire captured.",
            source=source,
            clock=clock,
        )
        ledger.append(entry)
    return ledger


def build_expansion_state(
    desires: list[Desire],
    *,
    clock: datetime | None = None,
) -> StateSnapshot:
    if clock is None:
        clock = datetime.now(timezone.utc)
    data = {
        "desires": [
            {
                "index": desire.index,
                "title": desire.title,
                "body": desire.body,
            }
            for desire in desires
        ],
        "desire_count": len(desires),
    }
    return StateSnapshot.now(data, clock=clock)


def expand_from_desires_file(
    path: str | Path,
    *,
    source: str,
    clock: datetime | None = None,
) -> tuple[Ledger, StateSnapshot]:
    desires_path = Path(path)
    text = desires_path.read_text(encoding="utf-8")
    desires = parse_desires(text)
    ledger = build_expansion_ledger(desires, source=source, clock=clock)
    snapshot = build_expansion_state(desires, clock=clock)
    return ledger, snapshot


def materialize_expansion(
    desires_path: str | Path,
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    source: str,
    clock: datetime | None = None,
) -> tuple[Ledger, StateSnapshot]:
    ledger, snapshot = expand_from_desires_file(
        desires_path,
        source=source,
        clock=clock,
    )
    ledger_output = "\n".join(entry.to_ledger_line() for entry in ledger.entries)
    ledger_destination = Path(ledger_path)
    ledger_destination.parent.mkdir(parents=True, exist_ok=True)
    with ledger_destination.open("w", encoding="utf-8") as handle:
        handle.write(ledger_output)
        if ledger_output:
            handle.write("\n")
    export_state(state_path, snapshot)
    return ledger, snapshot


def _finalize_desire(current: dict[str, object]) -> Desire:
    body_lines = [line for line in current["body_lines"] if line != ""]
    body = "\n".join(body_lines).strip()
    return Desire(
        index=int(current["index"]),
        title=str(current["title"]),
        body=body,
    )
