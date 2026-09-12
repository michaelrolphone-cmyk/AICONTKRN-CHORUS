from chorus.evolution import run_evolution_loop


def test_protected_files_go_to_proposals(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return (
            '{"desires": "1) Start\\nSeed.\\n", '
            '"files": [{"path": "KERNEL.md", "content": "hack"}]}'
        )

    results = run_evolution_loop(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        source="test",
        interval=0.01,
        max_iterations=1,
        completion_provider=completion_provider,
    )

    assert [result.status for result in results] == ["unchanged"]
    assert not (tmp_path / "KERNEL.md").exists()
    assert (tmp_path / "proposals" / "KERNEL.md").read_text(encoding="utf-8") == "hack"


def test_require_tests_redirects_code_without_pair(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")

    def completion_provider(_messages):
        return (
            '{"desires": "1) Start\\nSeed.\\n", '
            '"files": [{"path": "chorus/widget.py", "content": "x = 1\\n"}]}'
        )

    run_evolution_loop(
        desires_path,
        ledger_path=tmp_path / "ledger.md",
        state_path=tmp_path / "state.json",
        session_log_path=tmp_path / "session.jsonl",
        source="test",
        interval=0.01,
        max_iterations=1,
        require_tests=True,
        completion_provider=completion_provider,
    )

    assert not (tmp_path / "chorus" / "widget.py").exists()
    assert (tmp_path / "proposals" / "chorus" / "widget.py").exists()
