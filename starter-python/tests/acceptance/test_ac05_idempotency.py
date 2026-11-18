"""AC-05: repeating the same request key, session and alias returns the original reservation.

The replay must not consume another seat.
"""


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
