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
    completion_provider: Callable[[list[dict[str, str]]], str] | None = None,
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
) -> list[dict[str, str]]:
    ledger_excerpt = _read_tail_lines(ledger_path, limit=5)
    state_payload = _read_json(state_path)
    user_content = (
        "Current desires markdown:\n"
        f"{current_desires or '[none]'}\n\n"
        "Recent ledger entries (most recent last):\n"
        f"{ledger_excerpt or '[none]'}\n\n"
        "Current state snapshot JSON:\n"
        f"{json.dumps(state_payload, indent=2, sort_keys=True) if state_payload else '[none]'}\n\n"
        "Update the desires markdown to reflect the next self-evolution steps. "
        "Return ONLY valid JSON with keys: "
        "`desires` (string markdown list) and optional `files` (list of "
        "{path, content} objects). Use paths relative to the desires file "
        "directory. Do not include commentary or code fences."
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


def _apply_response(
    response: str,
    *,
    current_desires: str,
    desires_path: str | Path,
    ledger_path: str | Path,
    state_path: str | Path,
    source: str,
) -> tuple[str, str, str | None]:
    payload, error = _parse_response_payload(response)
    if payload is None:
        timestamp = datetime.now(timezone.utc).isoformat()
        return "invalid", timestamp, error or "Response did not contain a desires payload."

    desires_markdown = _normalize_desires_text(payload.desires)
    if not desires_markdown.strip():
        timestamp = datetime.now(timezone.utc).isoformat()
        return "invalid", timestamp, "Response JSON must include a non-empty 'desires' string."
    if desires_markdown.strip() == current_desires.strip():
        _write_files(payload.files, base_dir=_base_dir(desires_path))
        timestamp = datetime.now(timezone.utc).isoformat()
        return "unchanged", timestamp, None

    try:
        desires = parse_desires(desires_markdown)
    except Exception:
        desires = []
    if not desires:
        timestamp = datetime.now(timezone.utc).isoformat()
        return (
            "invalid",
            timestamp,
            "Desires must be a numbered list like '1) Title'.",
        )

    Path(desires_path).write_text(desires_markdown.strip() + "\n", encoding="utf-8")
    _write_files(payload.files, base_dir=_base_dir(desires_path))
    _, snapshot = materialize_expansion(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        source=source,
    )
    return "updated", snapshot.timestamp, None


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


def _normalize_api_base(api_base: str) -> str:
    return api_base.rstrip("/")


@dataclass(frozen=True)
class EvolutionPayload:
    desires: str
    files: list[dict[str, str]]


def _parse_response_payload(
    response: str,
) -> tuple[EvolutionPayload | None, str | None]:
    stripped = response.strip()
    if not stripped:
        return None, "Response was empty."
    candidate = _extract_json_candidate(stripped)
    if candidate:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            recovered = _recover_payload_from_invalid_json(candidate)
            if recovered is not None:
                return recovered, None
            return None, "Response JSON could not be parsed."
        if not isinstance(data, dict):
            return None, "Response JSON must be an object."
        desires = data.get("desires")
        if isinstance(desires, list):
            if not all(isinstance(item, str) for item in desires):
                return None, "Response JSON desires list entries must be strings."
            desires = _numbered_list(desires)
        if not isinstance(desires, str):
            return None, "Response JSON must include a 'desires' string."
        files = data.get("files", [])
        if files is None:
            files = []
        if not isinstance(files, list):
            return None, "Response JSON 'files' must be a list."
        normalized_files: list[dict[str, str]] = []
        for item in files:
            if not isinstance(item, dict):
                return None, "Each file entry must be an object."
            path = item.get("path")
            content = item.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                return None, "Each file entry must include string 'path' and 'content'."
            normalized_files.append({"path": path, "content": content})
        return EvolutionPayload(desires=desires, files=normalized_files), None

    recovered = _recover_payload_from_invalid_json(stripped)
    if recovered is not None:
        return recovered, None
    return EvolutionPayload(desires=stripped, files=[]), None


def _extract_json_candidate(response: str) -> str | None:
    if response.startswith("{"):
        return response
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    start = response.find("{")
    end = response.rfind("}")
    if start != -1 and end != -1 and end > start:
        return response[start : end + 1].strip()
    return None


def _recover_payload_from_invalid_json(response: str) -> EvolutionPayload | None:
    desires_text = _recover_desires_text(response)
    if desires_text:
        return EvolutionPayload(desires=desires_text, files=[])
    return None


def _recover_desires_text(response: str) -> str | None:
    match = re.search(r'"desires"\s*:\s*"(.*)', response, re.DOTALL)
    if not match:
        return None
    raw = match.group(1).rstrip()
    raw = re.sub(r'"\s*[,}]?\s*$', "", raw)
    raw = raw.strip()
    if not raw:
        return None
    normalized = (
        raw.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\r", "\r")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )
    return normalized.strip() or None


def _normalize_desires_text(desires: str) -> str:
    stripped = desires.strip()
    if not stripped:
        return ""
    if parse_desires(stripped):
        return stripped
    items = _extract_list_items(stripped.splitlines())
    if items:
        return _numbered_list(items)
    return _normalize_single_desire(stripped)


def _normalize_single_desire(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.strip():
            lines[index] = f"1) {line.strip()}"
            break
    return "\n".join(lines).strip()


def _extract_list_items(lines: Sequence[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        match = re.match(r"^\s*[-*•]\s+(.*)$", line)
        if match:
            text = match.group(1).strip()
            if text:
                items.append(text)
    return items


def _numbered_list(items: Sequence[str]) -> str:
    return "\n".join(f"{index}) {item.strip()}" for index, item in enumerate(items, start=1))


def _write_files(files: list[dict[str, str]], *, base_dir: Path) -> None:
    for item in files:
        relative_path = item["path"]
        content = item["content"]
        destination = (base_dir / relative_path).resolve()
        if base_dir not in destination.parents and destination != base_dir:
            raise ValueError(f"Refusing to write outside base directory: {relative_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def _base_dir(desires_path: str | Path) -> Path:
    return Path(desires_path).resolve().parent


def _maybe_run_bootstrap(
    bootstrap_path: str | Path | None,
    *,
    iteration: int,
    desires_path: str | Path,
    ledger_path: str | Path,
    state_path: str | Path,
    session_log_path: str | Path,
    source: str,
) -> None:
    if bootstrap_path is None:
        return
    path = Path(bootstrap_path)
    if not path.exists():
        return
    module_name = f"chorus_bootstrap_{iteration}"
    module = types.ModuleType(module_name)
    source = path.read_text(encoding="utf-8")
    exec(compile(source, str(path), "exec"), module.__dict__)
    bootstrap = getattr(module, "bootstrap", None)
    if not callable(bootstrap):
        raise ValueError("Bootstrap module must define a callable 'bootstrap' function")
    context = {
        "iteration": iteration,
        "desires_path": str(desires_path),
        "ledger_path": str(ledger_path),
        "state_path": str(state_path),
        "session_log_path": str(session_log_path),
        "source": source,
        "base_dir": str(_base_dir(desires_path)),
    }
    bootstrap(context)
