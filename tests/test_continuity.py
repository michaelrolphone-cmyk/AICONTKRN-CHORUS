from datetime import datetime, timezone
import json

from chorus.continuity import bootstrap_continuity, load_interactions, record_interaction


def test_record_and_load_interactions(tmp_path):
    clock = datetime(2026, 1, 6, tzinfo=timezone.utc)
    log_path = tmp_path / "session.jsonl"

    record_interaction(
        log_path,
        role="user",
        content="Hello",
        clock=clock,
    )
    record_interaction(
        log_path,
        role="assistant",
        content="Acknowledged",
        clock=clock,
    )

    records = load_interactions(log_path)

    assert [record.role for record in records] == ["user", "assistant"]
    assert records[0].ts == clock.isoformat()


def test_record_interaction_normalizes_empty_content(tmp_path):
    clock = datetime(2026, 1, 6, tzinfo=timezone.utc)
    log_path = tmp_path / "session.jsonl"

    record_interaction(
        log_path,
        role="assistant",
        content="",
        clock=clock,
    )

    records = load_interactions(log_path)

    assert records[0].content == "[empty]"


def test_bootstrap_continuity(tmp_path):
    clock = datetime(2026, 1, 7, tzinfo=timezone.utc)
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Continuity Hardening\nLedger-first growth.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    record, timestamp = bootstrap_continuity(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        source="test",
        clock=clock,
    )

    assert record.role == "system"
    assert timestamp == clock.isoformat()
    log_lines = session_log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(log_lines) == 1
    payload = json.loads(log_lines[0])
    assert payload["content"].startswith("Bootstrap continuity")
