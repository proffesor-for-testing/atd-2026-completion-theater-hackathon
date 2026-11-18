"""Integration: demo_data loads into a fixture dir and the running app reads it back."""
import json

import pytest

import demo_data
from support.fixture_app import FixtureApp


@pytest.fixture
def demo_app(tmp_path):
    instance = FixtureApp(tmp_path / "demo")
    demo_data.load_demo(instance.data_dir)
    instance.start()
    yield instance
    instance.stop()


def test_app_serves_demo_counts_and_cancelled_record(demo_app):
    status, sessions = demo_app.request("GET", "/sessions")
    _, cancelled = demo_app.request("GET", "/reservations/demo-0003")

    counts = {s["id"]: (s["activeCount"], s["remainingSeats"]) for s in sessions["sessions"]}
    assert status == 200
    assert counts == {"CT-101": (2, 0), "CT-102": (2, 1)}
    assert cancelled["status"] == "cancelled"


def test_demo_session_is_full_so_a_new_request_is_rejected(demo_app):
    status, body = demo_app.request("POST", "/reservations",
                                    json_body={"sessionId": "CT-101", "attendeeAlias": "Noor",
                                               "requestKey": "demo-new-noor"})

    assert status >= 400
    assert body["error"]


def test_loader_refuses_to_overwrite_an_unmarked_state_file(tmp_path):
    data_dir = tmp_path / "unmarked"
    data_dir.mkdir()
    (data_dir / "state.json").write_text(json.dumps({"sessions": [], "reservations": ["real"]}))

    with pytest.raises(RuntimeError, match="Refusing to reset"):
        demo_data.load_demo(data_dir)

    assert json.loads((data_dir / "state.json").read_text())["reservations"] == ["real"]
