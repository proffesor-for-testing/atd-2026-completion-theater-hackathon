"""Unit tests for storage.py: the local JSON state file (build-decisions.md)."""
from storage import load_state, save_state


def test_saved_state_loads_back_unchanged(tmp_path):
    path = tmp_path / "state.json"
    state = {
        "sessions": [{"id": "CT-101", "title": "Catching Ghost Databases", "capacity": 2}],
        "reservations": [],
    }

    save_state(path, state)

    assert load_state(path) == state
