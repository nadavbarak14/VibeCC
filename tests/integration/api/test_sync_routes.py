"""Integration tests for sync routes."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from vibecc.api.app import create_app
from vibecc.api.dependencies import (
    close_scheduler,
    close_state_store,
    get_scheduler,
    init_scheduler,
    init_state_store,
)
from vibecc.scheduler import SyncResult
from vibecc.state_store import StateStore


class MockScheduler:
    """Mock Scheduler for integration testing."""

    def __init__(self, store: StateStore):
        self._store = store

    def sync(self, project_id: str) -> SyncResult:
        """Process queue once - creates a pipeline and returns it."""
        # Create a pipeline to simulate starting one
        pipeline = self._store.create_pipeline(
            project_id=project_id,
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
            ticket_body="Test body",
        )
        return SyncResult(started=[pipeline], remaining=2)


@pytest.fixture
def db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)
    Path(f"{f.name}-wal").unlink(missing_ok=True)
    Path(f"{f.name}-shm").unlink(missing_ok=True)


@pytest.fixture
def store(db_path: str):
    """Get a StateStore instance for direct DB access."""
    return StateStore(db_path)


@pytest.fixture
def app(db_path: str, store: StateStore):
    """Create the FastAPI app with real database and mock scheduler."""
    app = create_app(db_path)
    init_state_store(db_path)

    # Create and inject mock scheduler
    scheduler = MockScheduler(store)
    init_scheduler(scheduler)

    # Override scheduler dependency to use our mock
    def override_get_scheduler():
        yield scheduler

    app.dependency_overrides[get_scheduler] = override_get_scheduler

    yield app
    close_scheduler()
    close_state_store()


@pytest.fixture
def client(app):
    """Create a test client."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.integration
class TestSyncEndpoint:
    """Tests for POST /projects/{project_id}/sync endpoint."""

    def test_sync_endpoint_processes_ticket(self, client: TestClient, store: StateStore) -> None:
        """API call triggers pipeline creation via scheduler."""
        # Create a project
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "repo": "owner/test-repo"},
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # Call sync
        sync_response = client.post(f"/api/v1/projects/{project_id}/sync")
        assert sync_response.status_code == 200

        data = sync_response.json()["data"]
        assert len(data["started"]) == 1
        assert data["started"][0]["ticket_id"] == "42"
        assert data["started"][0]["ticket_title"] == "Test ticket"
        assert data["remaining"] == 2

    def test_sync_endpoint_404_for_missing_project(self, client: TestClient) -> None:
        """Sync returns 404 for non-existent project."""
        sync_response = client.post("/api/v1/projects/nonexistent/sync")
        assert sync_response.status_code == 404
