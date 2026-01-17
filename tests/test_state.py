import json
from datetime import datetime, timezone

from chorus.state import StateSnapshot, export_state


def test_state_export(tmp_path):
    clock = datetime(2026, 1, 2, tzinfo=timezone.utc)
    snapshot = StateSnapshot.now({"T": 3, "foam": [1, 2]}, clock=clock)

    path = export_state(tmp_path / "state.json", snapshot)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["timestamp"] == snapshot.timestamp
    assert data["state"] == snapshot.data
