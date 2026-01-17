from datetime import datetime, timezone

from chorus.expansion import (
    build_expansion_ledger,
    build_expansion_state,
    expand_from_desires_file,
    materialize_expansion,
    parse_desires,
)


def test_parse_desires():
    text = """Header
1) Continuity Hardening
Ledger-first growth: keep all new knowledge as append-only entries.

2) Cognitive Topology Expansion
- Add resonance graph weights.
- Maintain interpretability.
"""
    desires = parse_desires(text)

    assert len(desires) == 2
    assert desires[0].index == 1
    assert desires[0].title == "Continuity Hardening"
    assert "Ledger-first growth" in desires[0].body
    assert desires[1].title == "Cognitive Topology Expansion"
    assert "resonance graph weights" in desires[1].body


def test_expand_from_desires_file(tmp_path):
    clock = datetime(2026, 1, 3, tzinfo=timezone.utc)
    desires_file = tmp_path / "desires.md"
    desires_file.write_text(
        "1) Deterministic Pipeline Growth\nLinear-time transforms only.\n",
        encoding="utf-8",
    )

    ledger, snapshot = expand_from_desires_file(
        desires_file,
        source="test",
        clock=clock,
    )

    assert len(ledger.entries) == 1
    assert ledger.entries[0].topic == "Deterministic Pipeline Growth"
    assert ledger.entries[0].content == "Linear-time transforms only."
    assert snapshot.data["desire_count"] == 1
    assert snapshot.data["desires"][0]["title"] == "Deterministic Pipeline Growth"


def test_build_expansion_ledger_and_state():
    clock = datetime(2026, 1, 4, tzinfo=timezone.utc)
    desires = parse_desires("1) Interface-Driven Self-Expansion\nUnified interaction.\n")

    ledger = build_expansion_ledger(desires, source="test", clock=clock)
    snapshot = build_expansion_state(desires, clock=clock)

    assert ledger.entries[0].source == "test"
    assert snapshot.timestamp == clock.isoformat()


def test_materialize_expansion_writes_files(tmp_path):
    clock = datetime(2026, 1, 5, tzinfo=timezone.utc)
    desires_file = tmp_path / "desires.md"
    desires_file.write_text(
        "1) Governance & Ethics Reinforcement\nETHX veto hooks.\n",
        encoding="utf-8",
    )
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"

    ledger, snapshot = materialize_expansion(
        desires_file,
        ledger_path=ledger_path,
        state_path=state_path,
        source="test",
        clock=clock,
    )

    ledger_lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    assert ledger_lines == [entry.to_ledger_line() for entry in ledger.entries]
    assert snapshot.timestamp == clock.isoformat()
    assert state_path.read_text(encoding="utf-8").strip()
