"""AC-04a: a third distinct request for CT-101 (capacity 2) is rejected and creates nothing."""

import pytest


def reserve(alias, key, session_id="CT-101"):
    return {"sessionId": session_id, "attendeeAlias": alias, "requestKey": key}


def test_third_distinct_request_for_full_session_is_rejected(app):
    app.start()
    app.request("POST", "/reservations", json_body=reserve("Ada", "K1"))
    app.request("POST", "/reservations", json_body=reserve("Ben", "K2"))

    status, body = app.request("POST", "/reservations", json_body=reserve("Cy", "K3"))

    assert 400 <= status < 500, f"expected a 4xx rejection, got {status}: {body}"
    assert body["error"], "rejection has no error text"
    _, sessions = app.request("GET", "/sessions")
    ct101 = next(s for s in sessions["sessions"] if s["id"] == "CT-101")
    assert ct101["activeCount"] == 2
    assert ct101["remainingSeats"] == 0
