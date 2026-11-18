"""Demo data for the seat desk: fictional attendees, never real people.

build_demo_state is pure. load_demo writes it into a fixture DATA_DIR through the
same marker check as app.py --reset, so an unmarked state file is never overwritten.

Run from starter-python/:
    python3 demo_data.py                 # loads into DATA_DIR (default .state/)
    python3 demo_data.py --data-dir DIR  # loads into another fixture directory
"""
import argparse
import json
from pathlib import Path

import app
import storage

BASE = Path(__file__).resolve().parent

# (reservation id, session, alias, request key, status). Ids are fixed so demos can refer to them.
DEMO_RESERVATIONS = [
    ("demo-0001", "CT-101", "Priya", "demo-ct101-priya", "active"),
    ("demo-0002", "CT-101", "Tomasz", "demo-ct101-tomasz", "active"),
    ("demo-0003", "CT-101", "Liam", "demo-ct101-liam", "cancelled"),
    ("demo-0004", "CT-102", "Mei", "demo-ct102-mei", "active"),
    ("demo-0005", "CT-102", "Kwame", "demo-ct102-kwame", "active"),
    ("demo-0006", "CT-102", "Hana", "demo-ct102-hana", "cancelled"),
]


def build_demo_state(sessions: list) -> dict:
    """Pure: seeded sessions plus the fixed demo reservations."""
    return {
        "sessions": sessions,
        "reservations": [
            {"id": rid, "sessionId": session, "attendeeAlias": alias,
             "requestKey": key, "status": status}
            for rid, session, alias, key, status in DEMO_RESERVATIONS
        ],
    }


def load_demo(data_dir: Path) -> Path:
    """Reset the marked fixture in data_dir, then write the demo state. Returns the state file."""
    state_file = app.reset_fixture(Path(data_dir))
    sessions = json.loads((BASE / "sessions.json").read_text())
    storage.save_state(state_file, build_demo_state(sessions))
    return state_file


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=app.DATA,
                        help="fixture directory to load (default: DATA_DIR or .state/)")
    args = parser.parse_args()
    print("Demo loaded:", load_demo(args.data_dir))


if __name__ == "__main__":
    main()
