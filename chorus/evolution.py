"""Self-evolution loop powered by LM Studio's API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import re
from typing import Callable, Iterable, Sequence
import types
from urllib import error as url_error
from urllib import request

from chorus.continuity import record_interaction
from chorus.expansion import materialize_expansion, parse_desires
from chorus.gates import has_paired_test, is_code, is_protected, needs_paired_test, proposal_path
from chorus.evolution_support import (
    _apply_response,
    _format_context_files,
    _maybe_run_bootstrap,
    _normalize_api_base,
    _read_json,
    _read_tail_lines,
    _read_text,
)


@dataclass(frozen=True)
class LmStudioConfig:
    api_base: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 512
    timeout: float = 30.0


class LmStudioRequestError(RuntimeError):
    """Raised when the LM Studio request cannot be completed."""


@dataclass(frozen=True)
class EvolutionResult:
    iteration: int
    timestamp: str
    status: str
    reason: str | None = None


def run_evolution_loop(
    desires_path: str | Path,
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    session_log_path: str | Path,
    source: str,
    api_base: str = "http://localhost:1234",
    model: str = "local-model",
    temperature: float = 0.7,
    max_tokens: int = 512,
    interval: float = 60.0,
    max_iterations: int | None = None,
    timeout: float = 30.0,
    bootstrap_path: str | Path | None = None,
    context_paths: Sequence[str | Path] | None = None,
    completion_provider: Callable[[list[dict[str, str]]], str] | None = None,
    apply_protected: bool = False,
    require_tests: bool = False,
) -> list[EvolutionResult]:
    if interval <= 0:
        raise ValueError("Interval must be positive")
    iteration = 0
    results: list[EvolutionResult] = []
    config = LmStudioConfig(
        api_base=api_base,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    if completion_provider is None:
        completion_provider = lambda messages: call_lm_studio_chat(config, messages)

    record_interaction(
        session_log_path,
        role="system",
        content=(
            "Self-evolution loop started. "
            f"Model={config.model}, API={_normalize_api_base(config.api_base)}."
        ),
    )
    print(
        "Self-evolution loop started. "
        f"Model={config.model}, API={_normalize_api_base(config.api_base)}.",
        flush=True,
    )

    while True:
        iteration += 1
        print(f"Iteration {iteration} started.", flush=True)
        _maybe_run_bootstrap(
            bootstrap_path,
            iteration=iteration,
            desires_path=desires_path,
            ledger_path=ledger_path,
            state_path=state_path,
            session_log_path=session_log_path,
            source=source,
        )
        current_desires = _read_text(desires_path)
        messages = _build_messages(
            current_desires,
            ledger_path=ledger_path,
            state_path=state_path,
            context_paths=context_paths,
        )
        record_interaction(
            session_log_path,
            role="user",
            content=messages[-1]["content"],
        )

        response_text: str | None = None
        try:
            response = completion_provider(messages)
            response_text = response
        except Exception as exc:  # pragma: no cover - defensive logging
            timestamp = datetime.now(timezone.utc).isoformat()
            record_interaction(
                session_log_path,
                role="system",
                content=(
                    "Evolution loop error: "
                    f"{exc} Raw response: {response_text or '[none]'}"
                ),
            )
            print(
                (
                    f"Iteration {iteration} error: {exc}. "
                    f"Raw response: {response_text or '[none]'}"
                ),
                flush=True,
            )
            results.append(
                EvolutionResult(
                    iteration=iteration,
                    timestamp=timestamp,
                    status="error",
                )
            )
        else:
            record_interaction(
                session_log_path,
                role="assistant",
                content=response,
            )
            status, timestamp, reason = _apply_response(
                response,
                current_desires=current_desires,
                desires_path=desires_path,
                ledger_path=ledger_path,
                state_path=state_path,
                source=source,
                apply_protected=apply_protected,
                require_tests=require_tests,
            )
            results.append(
                EvolutionResult(
                    iteration=iteration,
                    timestamp=timestamp,
                    status=status,
                    reason=reason,
                )
            )
            if status == "invalid":
                record_interaction(
                    session_log_path,
                    role="system",
                    content=f"Evolution loop raw response: {response_text}",
                )
                print(f"Raw response: {response_text}", flush=True)
            if reason:
                record_interaction(
                    session_log_path,
                    role="system",
                    content=f"Evolution loop status={status}. Reason: {reason}",
                )
                print(
                    f"Iteration {iteration} completed with status={status}. Reason: {reason}",
                    flush=True,
                )
            else:
                print(
                    f"Iteration {iteration} completed with status={status}.",
                    flush=True,
                )

        if max_iterations is not None and iteration >= max_iterations:
            return results
        time.sleep(interval)


def call_lm_studio_chat(config: LmStudioConfig, messages: Iterable[dict[str, str]]) -> str:
    payload = json.dumps(
        {
            "model": config.model,
            "messages": list(messages),
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
    ).encode("utf-8")
    target = f"{_normalize_api_base(config.api_base)}/v1/chat/completions"
    req = request.Request(
        target,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=config.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise LmStudioRequestError(
            (
                "LM Studio request timed out after "
                f"{config.timeout:.0f}s. "
                "Confirm LM Studio is running and reachable at "
                f"{_normalize_api_base(config.api_base)} or increase the timeout."
            )
        ) from exc
    except url_error.URLError as exc:
        raise LmStudioRequestError(
            (
                "LM Studio request failed. "
                "Confirm LM Studio is running and reachable at "
                f"{_normalize_api_base(config.api_base)}. "
                f"Details: {exc.reason}"
            )
        ) from exc
    return _extract_chat_content(data)


def _extract_chat_content(data: dict[str, object]) -> str:
    try:
        choice = data["choices"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected response format from LM Studio") from exc
    if not isinstance(choice, dict):
        raise ValueError("Unexpected response format from LM Studio")
    message = choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            first_call = tool_calls[0]
            if isinstance(first_call, dict):
                function = first_call.get("function")
                if isinstance(function, dict):
                    arguments = function.get("arguments")
                    if isinstance(arguments, str) and arguments.strip():
                        return arguments.strip()
    text = choice.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    raise ValueError("Empty response content from LM Studio")


def _build_messages(
    current_desires: str,
    *,
    ledger_path: str | Path,
    state_path: str | Path,
    context_paths: Sequence[str | Path] | None = None,
) -> list[dict[str, str]]:
    ledger_excerpt = _read_tail_lines(ledger_path, limit=5)
    state_payload = _read_json(state_path)
    context_payload = _format_context_files(context_paths)
    user_content = (
        "Current desires markdown:\n"
        f"{current_desires or '[none]'}\n\n"
        "Recent ledger entries (most recent last):\n"
        f"{ledger_excerpt or '[none]'}\n\n"
        "Current state snapshot JSON:\n"
        f"{json.dumps(state_payload, indent=2, sort_keys=True) if state_payload else '[none]'}\n\n"
        f"{context_payload}\n\n"
        "Update the desires markdown to reflect the next self-evolution steps. "
        "Return ONLY valid JSON with keys: "
        "`desires` (string markdown list) and optional `files` (list of "
        "{path, content} objects). Use paths relative to the desires file "
        "directory. When making code changes, include updated tests. "
        "Do not include commentary or code fences."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are CHORUS running a self-evolution loop. "
                "Rewrite the desires list to guide the next iteration."
            ),
        },
        {"role": "user", "content": user_content},
    ]
