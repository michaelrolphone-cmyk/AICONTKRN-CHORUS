from chorus.cli import main


def test_cli_expand(tmp_path, capsys):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Continuity\nSteady.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"

    result = main(
        [
            "expand",
            str(desires_path),
            str(ledger_path),
            str(state_path),
            "--source",
            "test",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Expansion materialized" in captured.out
    assert ledger_path.exists()
    assert state_path.exists()


def test_cli_bootstrap(tmp_path, capsys):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Continuity\nLedger.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    result = main(
        [
            "bootstrap",
            str(desires_path),
            str(ledger_path),
            str(state_path),
            str(session_log_path),
            "--source",
            "test",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Bootstrap complete" in captured.out
    assert session_log_path.exists()
