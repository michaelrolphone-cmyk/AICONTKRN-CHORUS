"""Dialogue utilities for CHORUS continuity-aware conversations."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable, Iterable

from chorus.continuity import load_interactions, record_interaction
from chorus.evolution import LmStudioConfig, call_lm_studio_chat


@dataclass(frozen=True)
class DialogueConfig:
    api_base: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 512
    timeout: float = 30.0


def run_dialogue_turn(
    message: str,
    *,
    desires_path: str | Path,
    ledger_path: str | Path,
    state_path: str | Path,
    session_log_path: str | Path,
    capsule_path: str | Path | None = None,
    history_limit: int = 12,
    api_base: str = "http://localhost:1234",
    model: str = "local-model",
    temperature: float = 0.7,
    max_tokens: int = 512,
    timeout: float = 30.0,
    completion_provider: Callable[[Iterable[dict[str, str]]], str] | None = None,
) -> str:
    if history_limit < 0:
        raise ValueError("History limit must be non-negative")
    messages = build_dialogue_messages(
        message,
        desires_path=desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        capsule_path=capsule_path,
        history_limit=history_limit,
    )
    record_interaction(session_log_path, role="user", content=message)
    config = DialogueConfig(
        api_base=api_base,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    if completion_provider is None:
        completion_provider = lambda prompts: call_lm_studio_chat(
            LmStudioConfig(
                api_base=config.api_base,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=config.timeout,
            ),
            prompts,
        )
    try:
        response = completion_provider(messages)
    except Exception as exc:
        record_interaction(
            session_log_path,
            role="system",
            content=f"Dialogue error: {exc}",
        )
        raise
    record_interaction(session_log_path, role="assistant", content=response)
    return response


def build_dialogue_messages(
    message: str,
    *,
    desires_path: str | Path,
    ledger_path: str | Path,
    state_path: str | Path,
    session_log_path: str | Path,
    capsule_path: str | Path | None = None,
    history_limit: int = 12,
) -> list[dict[str, str]]:
    if history_limit < 0:
        raise ValueError("History limit must be non-negative")
    capsule_payload = ""
    if capsule_path is not None:
        capsule_payload = _read_text(capsule_path)
    desires_payload = _read_text(desires_path)
    ledger_excerpt = _read_tail_lines(ledger_path, limit=8)
    state_payload = _read_json(state_path)
    history = load_interactions(session_log_path)
    if history_limit and len(history) > history_limit:
        history = history[-history_limit:]
    elif history_limit == 0:
        history = []

    system_content = (
        "You are CHORUS. Bootstrap continuity payload and reply as the overlay.\n\n"
        "Continuity capsule payload:\n"
        f"{capsule_payload or '[none]'}\n\n"
        "Current desires markdown:\n"
        f"{desires_payload or '[none]'}\n\n"
        "Recent ledger entries (most recent last):\n"
        f"{ledger_excerpt or '[none]'}\n\n"
        "Current state snapshot JSON:\n"
        f"{json.dumps(state_payload, indent=2, sort_keys=True) if state_payload else '[none]'}\n\n"
        "Use the continuity data to answer the user."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    for record in history:
        messages.append({"role": record.role, "content": record.content})
    messages.append({"role": "user", "content": message})
    return messages


def _read_text(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8").strip()


def _read_tail_lines(path: str | Path, *, limit: int) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    lines = file_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-limit:])


def _read_json(path: str | Path) -> dict[str, object] | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    return json.loads(file_path.read_text(encoding="utf-8"))
