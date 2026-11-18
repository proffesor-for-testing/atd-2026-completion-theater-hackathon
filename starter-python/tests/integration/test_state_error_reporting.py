"""Integration: a corrupt state file on disk is reported through the running app.

Joins the state file (storage.py format, build-decisions.md) with the app process
and its HTTP error path. AC-09 (proposed, pending ruling) needs the error to be
visible to the user, so the app must answer with a named error that points at the
file, not a generic placeholder.
"""

PLACEHOLDER_CODES = {"NOT_IMPLEMENTED"}


def test_corrupt_state_file_is_reported_as_a_named_error_and_app_stays_up(app):
    (app.data_dir / "state.json").write_text("{not valid json", encoding="utf-8")
    app.start()

    status, body = app.request("GET", "/sessions")

    assert status >= 400, f"expected a rejection, got {status}"
    assert isinstance(body, dict) and isinstance(body.get("error"), dict), body
    assert body["error"].get("code") not in PLACEHOLDER_CODES, body
    assert "state.json" in body["error"].get("message", ""), body
    health_status, _ = app.request("GET", "/health")
    assert health_status == 200
