"""AC-02: GET /sessions returns both seeded sessions with capacity, active count and remaining seats.

On a fresh reset the active counts are 0 and remaining seats equal capacity
(CT-101: 2 and 2, CT-102: 3 and 3). The shape follows api-contract.md.
"""
import pytest

EXPECTED_FRESH_SESSIONS = [
    {"id": "CT-101", "title": "Catching Ghost Databases", "capacity": 2,
     "activeCount": 0, "remainingSeats": 2},
    {"id": "CT-102", "title": "Tests That Can Fail", "capacity": 3,
     "activeCount": 0, "remainingSeats": 3},
]


def test_fresh_reset_lists_both_sessions_with_zero_active_and_full_seats(app):
    app.start()

    status, body = app.request("GET", "/sessions")

    assert status == 200
    assert body["sessions"] == EXPECTED_FRESH_SESSIONS
