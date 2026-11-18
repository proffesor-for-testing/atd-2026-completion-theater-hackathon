"""AC-08: invalid input is rejected with a clear error and changes no state."""
import pytest


def reserve(alias, key="K1", session_id="CT-101"):
    return {"sessionId": session_id, "attendeeAlias": alias, "requestKey": key}


def remaining_seats(app, session_id="CT-101"):
    _, sessions = app.request("GET", "/sessions")
    record = next(s for s in sessions["sessions"] if s["id"] == session_id)
    return record["activeCount"], record["remainingSeats"]


@pytest.mark.parametrize("alias", ["", "   ", "\t \n"], ids=["empty", "spaces", "tabs-newline"])
def test_blank_alias_is_rejected_without_state_change(app, alias):
    app.start()
    before = remaining_seats(app)

    status, body = app.request("POST", "/reservations", json_body=reserve(alias))

    assert 400 <= status < 500, f"blank alias was accepted: {status}: {body}"
    assert isinstance(body, dict) and body.get("error"), f"no error message: {body}"
    assert remaining_seats(app) == before


@pytest.mark.parametrize("body", [
    {"sessionId": "XX-999", "attendeeAlias": "Ada", "requestKey": "K1"},
    {"sessionId": "CT-101", "attendeeAlias": "Ada"},
], ids=["unknown-session", "missing-request-key"])
def test_unknown_session_or_missing_key_is_rejected_without_state_change(app, body):
    app.start()
    before = remaining_seats(app)

    status, reply = app.request("POST", "/reservations", json_body=body)

    assert 400 <= status < 500, f"invalid request was not a 4xx: {status}: {reply}"
    assert isinstance(reply, dict) and reply.get("error"), f"no error message: {reply}"
    assert remaining_seats(app) == before
