"""Shared fixtures and automatic markers.

Markers come from the folder: tests/unit -> unit, tests/acceptance -> acceptance.
"""
import pytest

from support.fixture_app import FixtureApp


def pytest_collection_modifyitems(items):
    for item in items:
        parts = item.path.parts
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
        elif "acceptance" in parts:
            item.add_marker(pytest.mark.acceptance)


@pytest.fixture
def app(tmp_path):
    """A freshly reset app instance with its own state directory. Not started."""
    instance = FixtureApp(tmp_path / "state")
    instance.reset()
    yield instance
    instance.stop()
