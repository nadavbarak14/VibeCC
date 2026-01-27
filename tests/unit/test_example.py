"""Example unit tests to verify testing infrastructure works."""

import pytest

from vibecc import __version__


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
