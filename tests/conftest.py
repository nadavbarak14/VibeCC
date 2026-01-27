"""Shared pytest fixtures and configuration."""

import pytest


# Register custom markers
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for test categorization."""
    config.addinivalue_line("markers", "unit: fast tests with no external dependencies")
    config.addinivalue_line("markers", "integration: component interaction tests")
    config.addinivalue_line("markers", "e2e: full pipeline tests")
    config.addinivalue_line("markers", "real: actual Claude Code invocation (local only)")


# Shared fixtures


@pytest.fixture
def sample_fixture():
    """Example fixture - replace with actual fixtures as needed."""
    return {"example": "data"}
