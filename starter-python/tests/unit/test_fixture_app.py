"""Unit tests for tests/support/fixture_app.py (the harness itself)."""
import socket

import pytest

from support.fixture_app import FixtureApp, free_port


def test_free_port_is_a_bindable_loopback_port():
    port = free_port()

    assert 1024 <= port <= 65535
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", port))


def test_reset_creates_marked_fixture_database_in_its_own_data_dir(tmp_path):
    instance = FixtureApp(tmp_path / "state")

    instance.reset()

    assert (instance.data_dir / "state.json").exists()
    assert (instance.data_dir / ".fixture-owner").exists()


def test_started_app_answers_health_and_stop_releases_the_port(app):
    app.start()

    status, body = app.request("GET", "/health")
    exit_code = app.stop()

    assert status == 200
    assert body["status"] == "scaffold"
    assert exit_code is not None
    with pytest.raises(OSError):
        app.request("GET", "/health")


def test_non_2xx_responses_are_returned_with_parsed_json_not_raised(app):
    app.start()

    status, body = app.request("GET", "/no-such-path")

    assert status == 501
    assert body["error"]["code"] == "NOT_IMPLEMENTED"


def test_stop_before_start_is_a_no_op(app):
    assert app.stop() is None
