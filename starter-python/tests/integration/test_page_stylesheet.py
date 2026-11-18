"""Integration: the stylesheet the page links to is served by the running app.

Joins ui.py (the link in the page) with the app process (the /static route).
"""
import urllib.request


def test_running_app_serves_the_stylesheet_as_css(app):
    app.start()

    with urllib.request.urlopen(f"{app.base_url}/static/style.css") as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read().decode("utf-8")

    assert content_type.startswith("text/css"), content_type
    assert "body" in body
