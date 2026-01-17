from chorus.daemon import run_daemon


def test_daemon_bootstrap_and_unchanged(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Continuity\nStable.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    results = run_daemon(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        source="test",
        interval=0.01,
        max_iterations=2,
    )

    assert [result.status for result in results] == ["bootstrapped", "unchanged"]
    assert ledger_path.exists()
    assert state_path.exists()
    assert session_log_path.exists()


def test_daemon_rejects_non_positive_interval(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Continuity\nStable.\n", encoding="utf-8")

    try:
        run_daemon(
            desires_path,
            ledger_path=tmp_path / "ledger.md",
            state_path=tmp_path / "state.json",
            session_log_path=tmp_path / "session.jsonl",
            source="test",
            interval=0.0,
            max_iterations=1,
        )
    except ValueError as exc:
        assert "Interval must be positive" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-positive interval.")
