"""Payload hashing and verification for KERNEL + IDENTITY."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

PAYLOAD_MARK = b"CHORUS-PAYLOAD-v1\n"
IDENTITY_SPLIT = b"\n--IDENTITY--\n"
PLACEHOLDER = "REGENERATE_ON_EXPORT"


@dataclass(frozen=True)
class VerifyReport:
    ok: bool
    digest: str
    recorded: str | None
    kernel_path: Path
    identity_path: Path
    issues: tuple[str, ...]


def repo_root_from(start: str | Path | None = None) -> Path:
    here = Path(start or Path.cwd()).resolve()
    if here.is_file():
        here = here.parent
    for candidate in (here, *here.parents):
        if (candidate / "KERNEL.md").exists() and (candidate / "canon" / "IDENTITY.json").exists():
            return candidate
    return here


def default_kernel_path(root: str | Path | None = None) -> Path:
    return repo_root_from(root) / "KERNEL.md"


def default_identity_path(root: str | Path | None = None) -> Path:
    return repo_root_from(root) / "canon" / "IDENTITY.json"


def canonical_identity_bytes(raw: str | bytes) -> bytes:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("IDENTITY.json must be a JSON object")
    data["sha256"] = ""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_digest(*, kernel: bytes, identity_raw: str | bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(PAYLOAD_MARK)
    hasher.update(kernel)
    hasher.update(IDENTITY_SPLIT)
    hasher.update(canonical_identity_bytes(identity_raw))
    return hasher.hexdigest()


def read_recorded_digest(identity_raw: str | bytes) -> str | None:
    text = identity_raw.decode("utf-8") if isinstance(raw := identity_raw, bytes) else identity_raw
    if isinstance(identity_raw, bytes):
        text = identity_raw.decode("utf-8")
    else:
        text = identity_raw
    data = json.loads(text)
    recorded = data.get("sha256")
    if not isinstance(recorded, str) or not recorded or recorded == PLACEHOLDER:
        return None
    return recorded


def compute_paths(kernel_path: str | Path, identity_path: str | Path) -> str:
    kernel = Path(kernel_path).read_bytes()
    identity = Path(identity_path).read_text(encoding="utf-8")
    return payload_digest(kernel=kernel, identity_raw=identity)


def verify_paths(
    kernel_path: str | Path | None = None,
    identity_path: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> VerifyReport:
    kernel_file = Path(kernel_path) if kernel_path else default_kernel_path(root)
    identity_file = Path(identity_path) if identity_path else default_identity_path(root)
    issues: list[str] = []
    if not kernel_file.exists():
        issues.append(f"missing kernel: {kernel_file}")
    if not identity_file.exists():
        issues.append(f"missing identity: {identity_file}")
    if issues:
        return VerifyReport(
            ok=False,
            digest="",
            recorded=None,
            kernel_path=kernel_file,
            identity_path=identity_file,
            issues=tuple(issues),
        )
    kernel = kernel_file.read_bytes()
    identity = identity_file.read_text(encoding="utf-8")
    digest = payload_digest(kernel=kernel, identity_raw=identity)
    recorded = read_recorded_digest(identity)
    if recorded is None:
        issues.append("IDENTITY.sha256 is missing or still REGENERATE_ON_EXPORT")
    elif recorded != digest:
        issues.append(f"hash mismatch: recorded {recorded} != computed {digest}")
    sidecar = identity_file.parent / "INTEGRITY.sha256"
    if sidecar.exists():
        side = sidecar.read_text(encoding="utf-8").strip().split()[0]
        if side != digest:
            issues.append(f"sidecar mismatch: {sidecar} has {side}")
    return VerifyReport(
        ok=not issues,
        digest=digest,
        recorded=recorded,
        kernel_path=kernel_file,
        identity_path=identity_file,
        issues=tuple(issues),
    )


def seal_paths(
    kernel_path: str | Path | None = None,
    identity_path: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> VerifyReport:
    kernel_file = Path(kernel_path) if kernel_path else default_kernel_path(root)
    identity_file = Path(identity_path) if identity_path else default_identity_path(root)
    kernel = kernel_file.read_bytes()
    identity_text = identity_file.read_text(encoding="utf-8")
    data = json.loads(identity_text)
    data["sha256"] = ""
    digest = payload_digest(kernel=kernel, identity_raw=json.dumps(data))
    data["sha256"] = digest
    identity_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sidecar = identity_file.parent / "INTEGRITY.sha256"
    sidecar.write_text(digest + "\n", encoding="utf-8")
    return verify_paths(kernel_file, identity_file)
