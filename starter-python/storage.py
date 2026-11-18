"""Local JSON state file for the seat desk (build-decisions.md).

Writes go to a temp file in the same directory and are moved into place with
os.replace, so a reader sees either the old state or the new state, never a
partial file.
"""
import json
import os
import tempfile
from pathlib import Path


def encode_state(state: dict) -> str:
    """Pure: state dict -> JSON text."""
    return json.dumps(state, indent=2, sort_keys=True) + "\n"


def decode_state(text: str) -> dict:
    """Pure: JSON text -> state dict."""
    return json.loads(text)


def save_state(path: Path, state: dict) -> None:
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(encode_state(state))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def load_state(path: Path) -> dict:
    return decode_state(Path(path).read_text(encoding="utf-8"))
