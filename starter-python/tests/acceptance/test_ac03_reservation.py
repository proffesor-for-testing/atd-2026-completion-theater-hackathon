"""AC-03: a valid request for CT-101 with alias Ada and key K1 creates an active reservation."""

REQUEST = {"sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": "K1"}


def test_valid_request_returns_active_reservation_with_id(app):
    app.start()

    status, body = app.request("POST", "/reservations", json_body=REQUEST)

    assert 200 <= status < 300, f"expected success, got {status}: {body}"
    assert isinstance(body, dict)
    assert body["id"], "reservation has no ID"
    assert body["sessionId"] == "CT-101"
    assert body["attendeeAlias"] == "Ada"
    assert body["requestKey"] == "K1"
    assert body["status"] == "active"
