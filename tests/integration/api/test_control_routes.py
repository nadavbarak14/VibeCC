"""Integration tests for control routes."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibecc.api.app import create_app
from vibecc.api.dependencies import (
    AutopilotStatus,
    close_orchestrator,
    close_state_store,
    get_orchestrator,
    init_orchestrator,
    init_state_store,
)
from vibecc.state_store import PipelineState, StateStore


class MockOrchestrator:
    """Mock Orchestrator for integration testing."""

    def __init__(self, store: StateStore):
        self._store = store
        self._running: dict[str, bool] = {}

    def start_autopilot(self, project_id: str) -> None:
        """Start autopilot for a project."""
        self._running[project_id] = True

    def stop_autopilot(self, project_id: str) -> None:
        """Stop autopilot for a project."""
        self._running[project_id] = False

    def get_autopilot_status(self, project_id: str) -> AutopilotStatus:
        """Get autopilot status for a project."""
        # Count active pipelines from store
        active_states = [
            PipelineState.CODING,
            PipelineState.TESTING,
            PipelineState.REVIEW,
        ]
        queued_states = [PipelineState.QUEUED]

        all_pipelines = self._store.list_pipelines(project_id=project_id)
        active_count = sum(1 for p in all_pipelines if p.pipeline_state in active_states)
        queued_count = sum(1 for p in all_pipelines if p.pipeline_state in queued_states)

        return AutopilotStatus(
            project_id=project_id,
            running=self._running.get(project_id, False),
            active_pipelines=active_count,
            queued_tickets=queued_count,
        )


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
    """Create the FastAPI app with real database and mock orchestrator."""
    app = create_app(db_path)
    init_state_store(db_path)

    # Create and inject mock orchestrator
    orchestrator = MockOrchestrator(store)
    init_orchestrator(orchestrator)

    # Override orchestrator dependency to use our mock
    def override_get_orchestrator():
        yield orchestrator

    app.dependency_overrides[get_orchestrator] = override_get_orchestrator

    yield app
    close_orchestrator()
    close_state_store()


@pytest.fixture
def client(app):
    """Create a test client."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.integration
class TestStartStopAutopilotFlow:
    """Tests for start/stop autopilot flow."""

    def test_start_stop_autopilot_flow(self, client: TestClient, store: StateStore) -> None:
        """Start -> check status -> stop -> check status."""
        # Create a project
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "repo": "owner/test-repo"},
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # Initially stopped
        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        assert status_response.status_code == 200
        assert status_response.json()["data"]["running"] is False

        # Start autopilot
        start_response = client.post(f"/api/v1/projects/{project_id}/autopilot/start")
        assert start_response.status_code == 200
        assert start_response.json()["data"]["message"] == "Autopilot started"

        # Check status - should be running
        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        assert status_response.status_code == 200
        assert status_response.json()["data"]["running"] is True

        # Stop autopilot
        stop_response = client.post(f"/api/v1/projects/{project_id}/autopilot/stop")
        assert stop_response.status_code == 200
        assert stop_response.json()["data"]["message"] == "Autopilot stopped"

        # Check status - should be stopped
        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        assert status_response.status_code == 200
        assert status_response.json()["data"]["running"] is False


@pytest.mark.integration
class TestStatusReflectsActivePipelines:
    """Tests for status reflecting active pipelines."""

    def test_status_reflects_active_pipelines(self, client: TestClient, store: StateStore) -> None:
        """Count updates correctly based on pipeline states."""
        # Create a project
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "repo": "owner/test-repo"},
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # Initially no pipelines
        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        assert status_response.status_code == 200
        data = status_response.json()["data"]
        assert data["active_pipelines"] == 0
        assert data["queued_tickets"] == 0

        # Create a queued pipeline
        p1 = store.create_pipeline(
            project_id=project_id,
            ticket_id="1",
            ticket_title="Queued Ticket",
            branch_name="ticket-1",
        )

        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        data = status_response.json()["data"]
        assert data["active_pipelines"] == 0
        assert data["queued_tickets"] == 1

        # Move to coding (active)
        store.update_pipeline(p1.id, state=PipelineState.CODING)

        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        data = status_response.json()["data"]
        assert data["active_pipelines"] == 1
        assert data["queued_tickets"] == 0

        # Add another queued pipeline
        store.create_pipeline(
            project_id=project_id,
            ticket_id="2",
            ticket_title="Another Queued Ticket",
            branch_name="ticket-2",
        )

        status_response = client.get(f"/api/v1/projects/{project_id}/autopilot")
        data = status_response.json()["data"]
        assert data["active_pipelines"] == 1
        assert data["queued_tickets"] == 1
