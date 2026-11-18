"""AC-03: GET /reservations/{id} returns the record that POST /reservations created."""

REQUEST = {"sessionId": "CT-101", "attendeeAlias": "Ada", "requestKey": "K1"}


def test_reading_a_created_reservation_returns_the_same_record(app):
    app.start()
    _, created = app.request("POST", "/reservations", json_body=REQUEST)

    status, body = app.request("GET", f"/reservations/{created['id']}")

    assert status == 200, f"expected 200, got {status}: {body}"
    assert body == created
