"""Unit tests for control routes."""

import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from vibecc.api.dependencies import (
    AutopilotStatus,
    get_orchestrator,
    get_state_store,
)
from vibecc.api.models import APIResponse
from vibecc.api.routes import control, projects
from vibecc.state_store import (
    ProjectNotFoundError,
    StateStore,
)


class MockOrchestrator:
    """Mock Orchestrator for testing."""

    def __init__(self):
        self._running: dict[str, bool] = {}
        self._active_pipelines: dict[str, int] = {}
        self._queued_tickets: dict[str, int] = {}

    def start_autopilot(self, project_id: str) -> None:
        """Start autopilot for a project."""
        self._running[project_id] = True

    def stop_autopilot(self, project_id: str) -> None:
        """Stop autopilot for a project."""
        self._running[project_id] = False

    def get_autopilot_status(self, project_id: str) -> AutopilotStatus:
        """Get autopilot status for a project."""
        return AutopilotStatus(
            project_id=project_id,
            running=self._running.get(project_id, False),
            active_pipelines=self._active_pipelines.get(project_id, 0),
            queued_tickets=self._queued_tickets.get(project_id, 0),
        )

    def set_counts(self, project_id: str, active: int, queued: int) -> None:
        """Set pipeline counts for testing."""
        self._active_pipelines[project_id] = active
        self._queued_tickets[project_id] = queued


@pytest.fixture
def store():
    """Create an in-memory StateStore."""
    s = StateStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def orchestrator():
    """Create a mock Orchestrator."""
    return MockOrchestrator()


@pytest.fixture
def app(store: StateStore, orchestrator: MockOrchestrator):
    """Create a test FastAPI app with mocked dependencies."""
    app = FastAPI()

    # Override state store dependency
    def override_get_state_store():
        yield store

    def override_get_orchestrator():
        yield orchestrator

    app.dependency_overrides[get_state_store] = override_get_state_store
    app.dependency_overrides[get_orchestrator] = override_get_orchestrator

    # Add exception handlers
    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(request: Request, exc: ProjectNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse[None](data=None, error="Project not found").model_dump(),
        )

    # Include routes
    app.include_router(control.router, prefix="/api/v1")
    app.include_router(projects.router, prefix="/api/v1")

    return app


@pytest.fixture
def client(app: FastAPI):
    """Create a test client."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def project(store: StateStore):
    """Create a test project."""
    return store.create_project(name="Test Project", repo="owner/repo")


@pytest.mark.unit
class TestGetAutopilotStatus:
    """Tests for GET /projects/{project_id}/autopilot."""

    def test_get_autopilot_status_stopped(
        self, client: TestClient, project, orchestrator: MockOrchestrator
    ) -> None:
        """Returns running=false when stopped."""
        response = client.get(f"/api/v1/projects/{project.id}/autopilot")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["project_id"] == project.id
        assert data["data"]["running"] is False
        assert data["data"]["active_pipelines"] == 0
        assert data["data"]["queued_tickets"] == 0
        assert data["error"] is None

    def test_get_autopilot_status_running(
        self, client: TestClient, project, orchestrator: MockOrchestrator
    ) -> None:
        """Returns running=true with counts when running."""
        orchestrator.start_autopilot(project.id)
        orchestrator.set_counts(project.id, active=2, queued=5)

        response = client.get(f"/api/v1/projects/{project.id}/autopilot")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["project_id"] == project.id
        assert data["data"]["running"] is True
        assert data["data"]["active_pipelines"] == 2
        assert data["data"]["queued_tickets"] == 5

    def test_get_autopilot_status_project_not_found(self, client: TestClient) -> None:
        """404 error when project doesn't exist."""
        response = client.get("/api/v1/projects/nonexistent-id/autopilot")

        assert response.status_code == 404
        data = response.json()
        assert data["data"] is None
        assert "not found" in data["error"].lower()


@pytest.mark.unit
class TestStartAutopilot:
    """Tests for POST /projects/{project_id}/autopilot/start."""

    def test_start_autopilot_success(
        self, client: TestClient, project, orchestrator: MockOrchestrator
    ) -> None:
        """200 with success message."""
        response = client.post(f"/api/v1/projects/{project.id}/autopilot/start")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["message"] == "Autopilot started"
        assert data["error"] is None

        # Verify orchestrator was called
        status = orchestrator.get_autopilot_status(project.id)
        assert status.running is True

    def test_start_autopilot_already_running(
        self, client: TestClient, project, orchestrator: MockOrchestrator
    ) -> None:
        """200 (idempotent) when already running."""
        orchestrator.start_autopilot(project.id)

        response = client.post(f"/api/v1/projects/{project.id}/autopilot/start")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["message"] == "Autopilot started"

    def test_start_autopilot_project_not_found(self, client: TestClient) -> None:
        """404 error when project doesn't exist."""
        response = client.post("/api/v1/projects/nonexistent-id/autopilot/start")

        assert response.status_code == 404
        data = response.json()
        assert data["data"] is None
        assert "not found" in data["error"].lower()


@pytest.mark.unit
class TestStopAutopilot:
    """Tests for POST /projects/{project_id}/autopilot/stop."""

    def test_stop_autopilot_success(
        self, client: TestClient, project, orchestrator: MockOrchestrator
    ) -> None:
        """200 with success message."""
        orchestrator.start_autopilot(project.id)

        response = client.post(f"/api/v1/projects/{project.id}/autopilot/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["message"] == "Autopilot stopped"
        assert data["error"] is None

        # Verify orchestrator was called
        status = orchestrator.get_autopilot_status(project.id)
        assert status.running is False

    def test_stop_autopilot_already_stopped(
        self, client: TestClient, project, orchestrator: MockOrchestrator
    ) -> None:
        """200 (idempotent) when already stopped."""
        response = client.post(f"/api/v1/projects/{project.id}/autopilot/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["message"] == "Autopilot stopped"

    def test_stop_autopilot_project_not_found(self, client: TestClient) -> None:
        """404 error when project doesn't exist."""
        response = client.post("/api/v1/projects/nonexistent-id/autopilot/stop")

        assert response.status_code == 404
        data = response.json()
        assert data["data"] is None
        assert "not found" in data["error"].lower()
