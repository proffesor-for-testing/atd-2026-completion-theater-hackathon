"""AC-05: repeating the same request key, session and alias returns the original reservation.

The replay must not consume another seat.
"""
import pytest


def reserve(alias, key, session_id="CT-101"):
    return {"sessionId": session_id, "attendeeAlias": alias, "requestKey": key}


def test_repeating_same_key_session_and_alias_returns_original_without_using_a_seat(app):
    app.start()
    _, original = app.request("POST", "/reservations", json_body=reserve("Ada", "K1"))

    status, replay = app.request("POST", "/reservations", json_body=reserve("Ada", "K1"))

    assert 200 <= status < 300, f"replay was rejected: {status}: {replay}"
    assert replay["id"] == original["id"]
    assert replay["status"] == "active"
    _, sessions = app.request("GET", "/sessions")
    ct101 = next(s for s in sessions["sessions"] if s["id"] == "CT-101")
    assert ct101["activeCount"] == 1
    assert ct101["remainingSeats"] == 1


@pytest.mark.parametrize("padded_alias", ["  Ada", "Ada  ", " Ada ", "\tAda\n"])
def test_replay_with_alias_differing_only_by_surrounding_spaces_returns_original(app, padded_alias):
    app.start()
    _, original = app.request("POST", "/reservations", json_body=reserve("Ada", "K2"))

    status, replay = app.request("POST", "/reservations", json_body=reserve(padded_alias, "K2"))

    assert 200 <= status < 300, f"replay was rejected: {status}: {replay}"
    assert replay["id"] == original["id"]
    _, sessions = app.request("GET", "/sessions")
    ct101 = next(s for s in sessions["sessions"] if s["id"] == "CT-101")
    assert ct101["activeCount"] == 1


@pytest.mark.parametrize(
    "other_session, other_alias",
    [("CT-102", "Ada"), ("CT-101", "Bob"), ("CT-101", "ada")],
    ids=["different-session", "different-alias", "different-alias-case"],
)
def test_reusing_key_with_different_session_or_alias_is_a_conflict_and_changes_nothing(
        app, other_session, other_alias):
    app.start()
    app.request("POST", "/reservations", json_body=reserve("Ada", "K3"))
    _, before = app.request("GET", "/sessions")

    status, body = app.request("POST", "/reservations",
                               json_body=reserve(other_alias, "K3", session_id=other_session))

    assert 400 <= status < 500, f"expected a 4xx conflict, got {status}: {body}"
    assert body.get("error"), f"conflict has no error: {body}"
    _, after = app.request("GET", "/sessions")
    assert after == before
