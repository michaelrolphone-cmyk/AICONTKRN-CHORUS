from datetime import datetime, timezone

from chorus.ledger import Ledger, LedgerEntry, parse_ledger_line


def test_ledger_entry_serialization_round_trip():
    clock = datetime(2026, 1, 1, tzinfo=timezone.utc)
    entry = LedgerEntry.now(
        type="FACT",
        topic="Continuity",
        content="Append-only ledger entries",
        source="test",
        clock=clock,
    )
    line = entry.to_ledger_line()
    parsed = parse_ledger_line(line)

    assert parsed == entry


def test_ledger_rejects_invalid_type():
    entry = LedgerEntry(
        ts="2026-01-01T00:00:00+00:00",
        type="INVALID",
        topic="Continuity",
        content="Invalid entry type",
        source="test",
    )

    try:
        entry.validate()
    except ValueError as exc:
        assert "Unsupported ledger entry type" in str(exc)
    else:
        raise AssertionError("Expected validation to fail")


def test_append_to_file(tmp_path):
    ledger = Ledger()
    entry = LedgerEntry(
        ts="2026-01-01T00:00:00+00:00",
        type="PREF",
        topic="Persistence",
        content="Write ledger line",
        source="test",
    )

    path = tmp_path / "ledger.md"
    ledger.append_to_file(path, entry)

    data = path.read_text(encoding="utf-8").strip()
    assert data == entry.to_ledger_line()
    assert ledger.entries == [entry]
