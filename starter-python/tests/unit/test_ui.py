"""Unit tests for ui.py: the pure function that renders the seat desk page.

Input is session records in the API shape (api-contract.md), so the page can only
show what the API reports. No server, no state file.
"""
import pytest

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


@pytest.mark.parametrize("field", ["sessionId", "attendeeAlias", "requestKey"])
def test_page_has_a_labelled_reservation_form_field(field):
    page = ui.render_page(SEED_SESSIONS)

    assert f'name="{field}"' in page
    assert f'for="{field}"' in page or f'id="{field}"' in page


def test_reservation_form_posts_to_reservations():
    page = ui.render_page(SEED_SESSIONS)

    assert "<form" in page
    assert "/reservations" in page


def test_page_reloads_seat_counts_from_sessions_and_has_a_counts_container():
    page = ui.render_page(SEED_SESSIONS)

    assert 'id="seat-counts"' in page
    assert "fetch('/sessions')" in page
