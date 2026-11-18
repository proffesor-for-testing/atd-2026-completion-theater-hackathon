"""Unit tests for ui.py: the pure function that renders the seat desk page.

Input is session records in the API shape (api-contract.md), so the page can only
show what the API reports. No server, no state file.
"""
import ui

SEED_SESSIONS = [
    {"id": "CT-101", "title": "Catching Ghost Databases", "capacity": 2,
     "activeCount": 0, "remainingSeats": 2},
    {"id": "CT-102", "title": "Tests That Can Fail", "capacity": 3,
     "activeCount": 0, "remainingSeats": 3},
]


def test_rendered_page_shows_each_session_id_title_and_remaining_seats():
    page = ui.render_page(SEED_SESSIONS)

    for session in SEED_SESSIONS:
        assert session["id"] in page
        assert session["title"] in page
        assert f"{session['remainingSeats']} remaining" in page
