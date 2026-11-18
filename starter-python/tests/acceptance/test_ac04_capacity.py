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


"""AC-04b: concurrent distinct requests for the last seat of CT-101.

Each batch is a fresh app with one seat already taken, so one seat remains.
Ten simultaneous distinct attempts must produce exactly one success and an
active count of 2. Ten batches of ten attempts probe races; they do not prove
their absence.
"""
from concurrent.futures import ThreadPoolExecutor

from support.fixture_app import FixtureApp

BATCHES = 10
ATTEMPTS_PER_BATCH = 10


def fire_concurrently(app, payloads):
    with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
        return list(pool.map(lambda p: app.request("POST", "/reservations", json_body=p), payloads))


@pytest.mark.parametrize("batch", range(BATCHES))
def test_concurrent_attempts_for_last_seat_give_exactly_one_success(tmp_path, batch):
    app = FixtureApp(tmp_path / f"batch-{batch}")
    app.reset()
    app.start()
    try:
        app.request("POST", "/reservations", json_body=reserve("Seed", f"SEED-{batch}"))
        attempts = [reserve(f"Attendee{i}", f"B{batch}-K{i}") for i in range(ATTEMPTS_PER_BATCH)]

        results = fire_concurrently(app, attempts)

        successes = [body for status, body in results if 200 <= status < 300]
        rejections = [(status, body) for status, body in results if not 200 <= status < 300]
        assert len(successes) == 1, f"expected exactly one success, got {len(successes)}"
        for status, body in rejections:
            assert 400 <= status < 500, f"rejection was not a 4xx: {status}: {body}"
        _, sessions = app.request("GET", "/sessions")
        ct101 = next(s for s in sessions["sessions"] if s["id"] == "CT-101")
        assert ct101["activeCount"] == 2
    finally:
        app.stop()
