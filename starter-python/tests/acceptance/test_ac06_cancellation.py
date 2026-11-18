"""AC-06: cancelling an active reservation releases exactly one seat."""


def reserve(alias, key, session_id="CT-101"):
    return {"sessionId": session_id, "attendeeAlias": alias, "requestKey": key}


def session_counts(app, session_id):
    _, sessions = app.request("GET", "/sessions")
    record = next(s for s in sessions["sessions"] if s["id"] == session_id)
    return record["activeCount"], record["remainingSeats"]


def test_cancelling_an_active_reservation_releases_exactly_one_seat(app):
    app.start()
    _, first = app.request("POST", "/reservations", json_body=reserve("Ada", "K1"))
    app.request("POST", "/reservations", json_body=reserve("Bob", "K2"))
    assert session_counts(app, "CT-101") == (2, 0)

    status, cancelled = app.request("POST", f"/reservations/{first['id']}/cancel", json_body={})

    assert 200 <= status < 300, f"cancel was rejected: {status}: {cancelled}"
    assert cancelled["id"] == first["id"]
    assert cancelled["status"] == "cancelled"
    assert session_counts(app, "CT-101") == (1, 1)
