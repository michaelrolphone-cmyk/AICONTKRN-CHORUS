"""Append-only ledger tooling for CHORUS continuity hardening."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ALLOWED_ENTRY_TYPES = {
    "FACT",
    "PREF",
    "PROJECT",
    "DECISION",
    "WARNING",
    "TODO",
    "PATCH",
    "ASSUMPTION",
}


@dataclass(frozen=True)
class LedgerEntry:
    ts: str
    type: str
    topic: str
    content: str
    source: str

    @classmethod
    def now(
        cls,
        *,
        type: str,
        topic: str,
        content: str,
        source: str,
        clock: datetime | None = None,
    ) -> "LedgerEntry":
        if clock is None:
            clock = datetime.now(timezone.utc)
        timestamp = clock.isoformat()
        return cls(
            ts=timestamp,
            type=type,
            topic=topic,
            content=content,
            source=source,
        )

    def validate(self) -> None:
        if self.type not in ALLOWED_ENTRY_TYPES:
            raise ValueError(f"Unsupported ledger entry type: {self.type}")
        for field_name, value in (
            ("ts", self.ts),
            ("topic", self.topic),
            ("content", self.content),
            ("source", self.source),
        ):
            if not value:
                raise ValueError(f"Ledger entry {field_name} must be non-empty")

    def to_ledger_line(self) -> str:
        self.validate()
        return (
            f'- {{ts:"{_escape(self.ts)}", type:"{_escape(self.type)}", '
            f'topic:"{_escape(self.topic)}", content:"{_escape(self.content)}", '
            f'source:"{_escape(self.source)}"}}'
        )


class Ledger:
    def __init__(self, entries: Iterable[LedgerEntry] | None = None) -> None:
        self._entries = list(entries or [])
        for entry in self._entries:
            entry.validate()

    @property
    def entries(self) -> list[LedgerEntry]:
        return list(self._entries)

    def append(self, entry: LedgerEntry) -> None:
        entry.validate()
        self._entries.append(entry)

    def extend(self, entries: Iterable[LedgerEntry]) -> None:
        for entry in entries:
            self.append(entry)

    def append_to_file(self, path: str | Path, entry: LedgerEntry) -> None:
        entry.validate()
        ledger_path = Path(path)
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(entry.to_ledger_line())
            handle.write("\n")
        self._entries.append(entry)


def parse_ledger_line(line: str) -> LedgerEntry:
    trimmed = line.strip()
    if not trimmed.startswith("- {") or not trimmed.endswith("}"):
        raise ValueError("Invalid ledger line format")
    payload = trimmed[3:-1]
    parts = _split_quoted_fields(payload)
    values: dict[str, str] = {}
    for part in parts:
        key, raw = part.split(":", 1)
        key = key.strip()
        raw_value = raw.strip()
        if not (raw_value.startswith("\"") and raw_value.endswith("\"")):
            raise ValueError("Ledger values must be quoted")
        values[key] = _unescape(raw_value[1:-1])
    entry = LedgerEntry(
        ts=values["ts"],
        type=values["type"],
        topic=values["topic"],
        content=values["content"],
        source=values["source"],
    )
    entry.validate()
    return entry


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def _unescape(value: str) -> str:
    return value.replace("\\\"", "\"").replace("\\\\", "\\")


def _split_quoted_fields(payload: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    in_quotes = False
    escape = False
    for char in payload:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\":
            current.append(char)
            escape = True
            continue
        if char == "\"":
            current.append(char)
            in_quotes = not in_quotes
            continue
        if char == "," and not in_quotes:
            fields.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if in_quotes:
        raise ValueError("Unterminated quoted value in ledger line")
    if current:
        fields.append("".join(current).strip())
    return fields
