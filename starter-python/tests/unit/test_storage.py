"""Unit tests for storage.py: the local JSON state file (build-decisions.md)."""
import pytest

import storage
from storage import load_state, save_state


def test_saved_state_loads_back_unchanged(tmp_path):
    path = tmp_path / "state.json"
    state = {
        "sessions": [{"id": "CT-101", "title": "Catching Ghost Databases", "capacity": 2}],
        "reservations": [],
    }

    save_state(path, state)

    assert load_state(path) == state


OLD_STATE = {"sessions": [{"id": "CT-101", "capacity": 2}], "reservations": []}


def _replace_fails(*args, **kwargs):
    raise OSError("simulated crash before the move into place")


def _unserialisable_state():
    return {"sessions": [object()]}


@pytest.mark.parametrize(
    "break_write, new_state",
    [
        pytest.param(lambda monkeypatch: monkeypatch.setattr(storage.os, "replace", _replace_fails),
                     {"sessions": [], "reservations": ["new"]}, id="crash-before-move"),
        pytest.param(lambda monkeypatch: None, _unserialisable_state(), id="unserialisable-state"),
    ],
)
def test_failed_save_leaves_old_file_and_no_temp_files(tmp_path, monkeypatch, break_write, new_state):
    path = tmp_path / "state.json"
    storage.save_state(path, OLD_STATE)
    break_write(monkeypatch)

    with pytest.raises((OSError, TypeError)):
        storage.save_state(path, new_state)

    assert storage.load_state(path) == OLD_STATE
    assert sorted(p.name for p in tmp_path.iterdir()) == ["state.json"]
