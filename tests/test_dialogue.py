import pytest

from chorus.dialogue import build_dialogue_messages, run_dialogue_turn
from chorus.evolution import LmStudioRequestError


def test_build_dialogue_messages_includes_continuity_payloads(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Persist\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    ledger_path.write_text("[ledger]\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text('{"state": {"desire_count": 1}}\n', encoding="utf-8")
    session_log_path = tmp_path / "session.jsonl"
    capsule_path = tmp_path / "capsule.md"
    capsule_path.write_text("Capsule context", encoding="utf-8")

    messages = build_dialogue_messages(
        "Hello",
        desires_path=desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        capsule_path=capsule_path,
        history_limit=0,
    )

    system_message = messages[0]["content"]
    assert "Capsule context" in system_message
    assert "1) Persist" in system_message
    assert "[ledger]" in system_message
    assert "desire_count" in system_message


def test_run_dialogue_turn_records_interactions(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Persist\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    ledger_path.write_text("[ledger]\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text('{"state": {"desire_count": 1}}\n', encoding="utf-8")
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return "Acknowledged"

    response = run_dialogue_turn(
        "Hello",
        desires_path=desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        capsule_path=None,
        history_limit=0,
        completion_provider=completion_provider,
    )

    assert response == "Acknowledged"
    log_lines = session_log_path.read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 2
    assert "Hello" in log_lines[0]
    assert "Acknowledged" in log_lines[1]


def test_run_dialogue_turn_logs_lm_studio_errors(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Persist\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    ledger_path.write_text("[ledger]\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    state_path.write_text('{"state": {"desire_count": 1}}\n', encoding="utf-8")
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        raise LmStudioRequestError("LM Studio request failed.")

    with pytest.raises(LmStudioRequestError):
        run_dialogue_turn(
            "Hello",
            desires_path=desires_path,
            ledger_path=ledger_path,
            state_path=state_path,
            session_log_path=session_log_path,
            capsule_path=None,
            history_limit=0,
            completion_provider=completion_provider,
        )

    log_lines = session_log_path.read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 2
    assert "Dialogue error" in log_lines[1]
