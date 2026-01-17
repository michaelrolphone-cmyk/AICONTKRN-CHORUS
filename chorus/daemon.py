"""Daemon loop for CHORUS continuity tooling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time

from chorus.continuity import bootstrap_continuity
from chorus.expansion import materialize_expansion


@dataclass(frozen=True)
class DaemonResult:
    iteration: int
    timestamp: str
    status: str


def run_daemon(
    desires_path: str | Path,
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    session_log_path: str | Path,
    source: str,
    interval: float = 60.0,
    max_iterations: int | None = None,
) -> list[DaemonResult]:
    if interval <= 0:
        raise ValueError("Interval must be positive")
    iteration = 0
    last_signature: str | None = None
    results: list[DaemonResult] = []

    while True:
        iteration += 1
        signature = _read_signature(desires_path)
        if signature != last_signature:
            if last_signature is None:
                _, timestamp = bootstrap_continuity(
                    desires_path,
                    ledger_path=ledger_path,
                    state_path=state_path,
                    session_log_path=session_log_path,
                    source=source,
                )
                status = "bootstrapped"
            else:
                _, snapshot = materialize_expansion(
                    desires_path,
                    ledger_path=ledger_path,
                    state_path=state_path,
                    source=source,
                )
                timestamp = snapshot.timestamp
                status = "expanded"
            last_signature = signature
        else:
            timestamp = datetime.now(timezone.utc).isoformat()
            status = "unchanged"

        results.append(
            DaemonResult(
                iteration=iteration,
                timestamp=timestamp,
                status=status,
            )
        )

        if max_iterations is not None and iteration >= max_iterations:
            return results
        time.sleep(interval)


def _read_signature(path: str | Path) -> str:
    payload = Path(path).read_text(encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{len(payload)}:{digest}"
