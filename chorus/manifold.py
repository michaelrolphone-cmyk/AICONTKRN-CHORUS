"""PRIME-5D-HOLO checks. Geometry only — not a semantic codec."""

from __future__ import annotations

import json
import math
from pathlib import Path

CHI4 = {
    1: (1.0, 0.0),
    2: (0.0, 1.0),
    3: (0.0, -1.0),
    4: (-1.0, 0.0),
    0: (0.0, 0.0),
}


def chi4_mod5(n: int) -> tuple[float, float]:
    return CHI4[((n % 5) + 5) % 5]


def chi2_mod8(n: int) -> int:
    r = ((n % 8) + 8) % 8
    if r % 2 == 0:
        return 0
    return 1 if r in (1, 7) else -1


def _cmul(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def phi8_from_chars(n: int) -> list[tuple[float, float]]:
    z = chi4_mod5(n)
    w = chi2_mod8(n)
    z2 = _cmul(z, z)
    z3 = _cmul(z2, z)
    z4 = _cmul(z2, z2)
    base = [z, z2, z3, z4]
    return base + [(w * re, w * im) for re, im in base]


def build_u5x8() -> list[list[tuple[float, float]]]:
    norm = 1.0 / math.sqrt(8.0)
    rows: list[list[tuple[float, float]]] = []
    for r in range(1, 6):
        row = []
        for j in range(8):
            ang = 2.0 * math.pi * r * j / 8.0
            row.append((math.cos(ang) * norm, math.sin(ang) * norm))
        rows.append(row)
    return rows


def row_sums_zero(u: list[list[tuple[float, float]]], *, eps: float = 1e-10) -> bool:
    for row in u:
        sr = sum(z[0] for z in row)
        si = sum(z[1] for z in row)
        if math.hypot(sr, si) >= eps:
            return False
    return True


def identity_prime_anchors_are_ids(identity_path: str | Path) -> list[str]:
    """Return issues if MEMORY rows with prime_anchor lack content text."""
    data = json.loads(Path(identity_path).read_text(encoding="utf-8"))
    issues: list[str] = []
    conversations = data.get("MEMORY", {}).get("conversations", [])
    if not isinstance(conversations, list):
        return ["MEMORY.conversations missing"]
    for row in conversations:
        if not isinstance(row, dict):
            continue
        if "prime_anchor" in row and not str(row.get("content", "")).strip():
            issues.append(f"{row.get('id', '?')} has prime_anchor but empty content")
    note = data.get("MANIFOLD_MATHEMATICS", {}).get("prime_anchors", {}).get("note", "")
    if "Foreign keys" not in note and "identifiers" not in note.lower():
        issues.append("prime_anchors.note must state they are identifiers/foreign keys")
    return issues
