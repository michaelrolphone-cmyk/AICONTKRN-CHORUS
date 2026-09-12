"""Helpers for the evolution loop (write gates + payload parse)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Sequence
import types

from chorus.expansion import materialize_expansion, parse_desires
from chorus.gates import has_paired_test, is_protected, needs_paired_test, proposal_path


def _apply_response(
    response: str,
    *,
    current_desires: str,
    desires_path: str | Path,
    ledger_path: str | Path,
    state_path: str | Path,
    source: str,
    apply_protected: bool = False,
    require_tests: bool = False,
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
        _write_files(payload.files, base_dir=_base_dir(desires_path), apply_protected=apply_protected, require_tests=require_tests)
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
    _write_files(payload.files, base_dir=_base_dir(desires_path), apply_protected=apply_protected, require_tests=require_tests)
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


def _format_context_files(context_paths: Sequence[str | Path] | None) -> str:
    if not context_paths:
        return "Context files: [none]"
    sections: list[str] = ["Context files:"]
    for context_path in context_paths:
        file_path = Path(context_path)
        if not file_path.exists():
            sections.append(f"- {file_path}: [missing]")
            continue
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            content = "[empty]"
        sections.append(f"--- {file_path} ---\n{content}")
    return "\n\n".join(sections)


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
    if response.startswith("{ "):
        return response
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
    match = re.search(r'"desires"\s*:', response)
    if not match:
        return None
    index = match.end()
    while index < len(response) and response[index].isspace():
        index += 1
    if index >= len(response) or response[index] != '"':
        return None
    index += 1
    buffer: list[str] = []
    escape = False
    while index < len(response):
        char = response[index]
        if escape:
            if char == "n":
                buffer.append("\n")
            elif char == "t":
                buffer.append("\t")
            elif char == "r":
                buffer.append("\r")
            elif char == "b":
                buffer.append("\b")
            elif char == "f":
                buffer.append("\f")
            elif char in ("\\", '"', "/"):
                buffer.append(char)
            elif char == "u" and index + 4 < len(response):
                hex_value = response[index + 1 : index + 5]
                if all(c in "0123456789abcdefABCDEF" for c in hex_value):
                    buffer.append(chr(int(hex_value, 16)))
                    index += 4
                else:
                    buffer.append("\\u")
            else:
                buffer.append("\\")
                buffer.append(char)
            escape = False
            index += 1
            continue
        if char == "\\":
            escape = True
            index += 1
            continue
        if char == '"':
            probe = index + 1
            while probe < len(response) and response[probe].isspace():
                probe += 1
            if probe >= len(response) or response[probe] in (",", "}"):
                break
            buffer.append(char)
            index += 1
            continue
        buffer.append(char)
        index += 1
    recovered = "".join(buffer).strip()
    return recovered or None


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


def _write_files(
    files: list[dict[str, str]],
    *,
    base_dir: Path,
    apply_protected: bool = False,
    require_tests: bool = False,
) -> None:
    offered = [item["path"] for item in files]
    for item in files:
        relative_path = item["path"]
        content = item["content"]
        gated = False
        if is_protected(relative_path) and not apply_protected:
            relative_path = proposal_path(relative_path)
            gated = True
        elif require_tests and needs_paired_test(relative_path) and not has_paired_test(relative_path, offered):
            relative_path = proposal_path(relative_path)
            gated = True
        destination = (base_dir / relative_path).resolve()
        if base_dir not in destination.parents and destination != base_dir:
            raise ValueError(f"Refusing to write outside base directory: {relative_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        if gated:
            continue


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
