"""AC-01 (UI part): opening the app shows the two seeded sessions.

HTTP-only check: the page served at / must contain both seeded sessions with
their titles and remaining seats. Browser behaviour is checked manually and
recorded separately (build-decisions.md, Open).
"""


def test_opening_the_ui_shows_both_seeded_sessions(app):
    app.start()

    status, body = app.request("GET", "/")

    assert status == 200
    assert isinstance(body, str), "expected an HTML page, not JSON"
    for expected in ("CT-101", "Catching Ghost Databases", "CT-102", "Tests That Can Fail"):
        assert expected in body, f"UI page does not show {expected!r}"
