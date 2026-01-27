"""Example unit tests to verify testing infrastructure works."""

import pytest

from vibecc import __version__, get_version


@pytest.mark.unit
def test_version_exists():
    """Verify that version is defined."""
    assert __version__ is not None


@pytest.mark.unit
def test_version_format():
    """Verify that version follows semver format."""
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


@pytest.mark.unit
def test_get_version():
    """Verify get_version returns the correct version."""
    assert get_version() == __version__
    assert get_version() == "0.1.0"
