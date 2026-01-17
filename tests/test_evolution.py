import pytest

from chorus.evolution import _extract_chat_content, run_evolution_loop


def test_evolution_loop_updates_desires(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '{"desires": "1) Next Step\\nAdvance.\\n"}'

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

    assert [result.status for result in results] == ["updated"]
    assert "Next Step" in desires_path.read_text(encoding="utf-8")
    assert ledger_path.exists()
    assert state_path.exists()
    assert session_log_path.exists()


def test_evolution_loop_logs_progress_to_stdout(tmp_path, capsys):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '{"desires": "1) Next Step\\nAdvance.\\n"}'

    run_evolution_loop(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        source="test",
        interval=0.01,
        max_iterations=1,
        completion_provider=completion_provider,
    )

    output = capsys.readouterr().out
    assert "Self-evolution loop started." in output
    assert "Iteration 1 started." in output
    assert "Iteration 1 completed with status=updated." in output


def test_evolution_loop_rejects_invalid_response(tmp_path, capsys):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '{"desires": "Not a numbered list."}'

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

    assert [result.status for result in results] == ["invalid"]
    assert results[0].reason == "Desires must be a numbered list like '1) Title'."
    assert desires_path.read_text(encoding="utf-8").startswith("1) Start")
    output = capsys.readouterr().out
    assert "status=invalid" in output
    assert "Reason: Desires must be a numbered list like '1) Title'." in output
    assert 'Raw response: {"desires": "Not a numbered list."}' in output


def test_evolution_loop_normalizes_bulleted_desires(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '{"desires": "- First desire\\n- Second desire\\n"}'

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

    assert [result.status for result in results] == ["updated"]
    contents = desires_path.read_text(encoding="utf-8")
    assert contents.startswith("1) First desire")
    assert "2) Second desire" in contents


def test_evolution_loop_accepts_json_desires_list(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '{\"desires\": [\"First desire\", \"Second desire\"]}'

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

    assert [result.status for result in results] == ["updated"]
    contents = desires_path.read_text(encoding="utf-8")
    assert contents.startswith("1) First desire")
    assert "2) Second desire" in contents


def test_evolution_loop_parses_fenced_json_payload(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '```json\n{\n  "desires": "1) Next\\nAdvance.\\n"\n}\n```'

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

    assert [result.status for result in results] == ["updated"]
    assert "1) Next" in desires_path.read_text(encoding="utf-8")


def test_evolution_loop_logs_raw_response_on_error(tmp_path, capsys):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        raise ValueError("LM Studio unreachable")

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

    assert [result.status for result in results] == ["error"]
    output = capsys.readouterr().out
    assert "error: LM Studio unreachable" in output
    assert "Raw response: [none]" in output


def test_evolution_loop_writes_files_and_reloads_bootstrap(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"
    bootstrap_path = tmp_path / "bootstrap.py"
    marker_path = tmp_path / "marker.txt"

    bootstrap_path.write_text(
        "def bootstrap(context):\n"
        "    with open(context['base_dir'] + '/marker.txt', 'w', encoding='utf-8') as handle:\n"
        "        handle.write('v1')\n",
        encoding="utf-8",
    )

    call_count = {"count": 0}

    def completion_provider(_messages):
        call_count["count"] += 1
        if call_count["count"] == 1:
            bootstrap_path.write_text(
                "def bootstrap(context):\n"
                "    with open(context['base_dir'] + '/marker.txt', 'w', encoding='utf-8') as handle:\n"
                "        handle.write('v2')\n",
                encoding="utf-8",
            )
        return (
            '{\"desires\": \"1) Start\\nSeed.\\n\", '
            '\"files\": [{\"path\": \"notes.txt\", \"content\": \"updated\"}]}'
        )

    results = run_evolution_loop(
        desires_path,
        ledger_path=ledger_path,
        state_path=state_path,
        session_log_path=session_log_path,
        source="test",
        interval=0.01,
        max_iterations=2,
        bootstrap_path=bootstrap_path,
        completion_provider=completion_provider,
    )

    assert [result.status for result in results] == ["unchanged", "unchanged"]
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "updated"
    assert marker_path.read_text(encoding="utf-8") == "v2"


def test_extract_chat_content_uses_tool_call_arguments():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"function": {"arguments": '{"desires": "1) Next\\nAdvance."}'}}
                    ],
                }
            }
        ]
    }

    assert _extract_chat_content(payload) == '{"desires": "1) Next\\nAdvance."}'


def test_extract_chat_content_falls_back_to_text():
    payload = {"choices": [{"text": '{"desires": "1) Next\\nAdvance."}'}]}

    assert _extract_chat_content(payload) == '{"desires": "1) Next\\nAdvance."}'


def test_extract_chat_content_raises_on_empty():
    payload = {"choices": [{"message": {"content": ""}}]}

    with pytest.raises(ValueError, match="Empty response content"):
        _extract_chat_content(payload)


def test_evolution_loop_recovers_invalid_json_with_newlines(tmp_path):
    desires_path = tmp_path / "desires.md"
    desires_path.write_text("1) Start\nSeed.\n", encoding="utf-8")
    ledger_path = tmp_path / "ledger.md"
    state_path = tmp_path / "state.json"
    session_log_path = tmp_path / "session.jsonl"

    def completion_provider(_messages):
        return '{\n  "desires": "- First desire\n- Second desire\n"\n}'

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

    assert [result.status for result in results] == ["updated"]
    contents = desires_path.read_text(encoding="utf-8")
    assert contents.startswith("1) First desire")
    assert "2) Second desire" in contents
