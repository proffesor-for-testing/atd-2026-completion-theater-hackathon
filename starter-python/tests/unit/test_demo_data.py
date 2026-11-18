"""Unit tests for demo_data.py: plausible fictional reservations for demos (no real people)."""
import json
from pathlib import Path

import pytest

import demo_data

SEED_SESSIONS = json.loads((Path(demo_data.__file__).resolve().parent / "sessions.json").read_text())


@pytest.fixture
def demo_state():
    return demo_data.build_demo_state(SEED_SESSIONS)


def test_demo_state_keeps_the_seeded_sessions_unchanged(demo_state):
    assert demo_state["sessions"] == SEED_SESSIONS


def test_active_reservations_never_exceed_session_capacity(demo_state):
    for session in demo_state["sessions"]:
        active = [r for r in demo_state["reservations"]
                  if r["sessionId"] == session["id"] and r["status"] == "active"]
        assert len(active) <= session["capacity"], session["id"]


def test_every_reservation_points_at_a_seeded_session_with_a_valid_shape(demo_state):
    session_ids = {s["id"] for s in demo_state["sessions"]}
    keys = [r["requestKey"] for r in demo_state["reservations"]]
    ids = [r["id"] for r in demo_state["reservations"]]
    for r in demo_state["reservations"]:
        assert r["sessionId"] in session_ids
        assert r["status"] in {"active", "cancelled"}
        assert r["attendeeAlias"] == r["attendeeAlias"].strip() != ""
        assert "@" not in r["attendeeAlias"]
    assert len(set(keys)) == len(keys)
    assert len(set(ids)) == len(ids)


def test_demo_shows_a_full_session_and_a_cancelled_reservation(demo_state):
    statuses = {(r["sessionId"], r["status"]) for r in demo_state["reservations"]}
    full = [s for s in demo_state["sessions"]
            if sum(1 for r in demo_state["reservations"]
                   if r["sessionId"] == s["id"] and r["status"] == "active") == s["capacity"]]

    assert full, "at least one session should be full so the capacity error can be shown"
    assert any(status == "cancelled" for _, status in statuses)
