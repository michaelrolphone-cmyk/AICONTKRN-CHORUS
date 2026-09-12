"""Write gates for the evolution loop."""

from __future__ import annotations

from pathlib import Path

PROTECTED_NAMES = {
    "KERNEL.md",
    "canon/IDENTITY.json",
    "canon/INTEGRITY.sha256",
    "CHORUS_TRANSFER_CAPSULE.md",
    "chorus/integrity.py",
    "chorus/gates.py",
    "chorus/manifold.py",
}

CODE_SUFFIXES = {".py"}


def normalize_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_protected(path: str) -> bool:
    rel = normalize_rel(path)
    if rel in PROTECTED_NAMES:
        return True
    name = Path(rel).name
    return name in {"KERNEL.md", "IDENTITY.json", "INTEGRITY.sha256"}


def is_code(path: str) -> bool:
    return Path(normalize_rel(path)).suffix in CODE_SUFFIXES


def proposal_path(path: str) -> str:
    rel = normalize_rel(path)
    if rel.startswith("proposals/"):
        return rel
    return f"proposals/{rel}"


def needs_paired_test(path: str) -> bool:
    rel = normalize_rel(path)
    return rel.startswith("chorus/") and rel.endswith(".py")


def has_paired_test(path: str, file_paths: list[str]) -> bool:
    rel = normalize_rel(path)
    stem = Path(rel).stem
    expected = f"tests/test_{stem}.py"
    normalized = {normalize_rel(p) for p in file_paths}
    return expected in normalized
