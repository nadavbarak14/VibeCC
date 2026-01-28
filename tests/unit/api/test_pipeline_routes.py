"""Unit tests for pipeline routes."""

import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from vibecc.api.dependencies import get_state_store
from vibecc.api.models import APIResponse
from vibecc.api.routes import pipelines, projects
from vibecc.state_store import (
    PipelineNotFoundError,
    PipelineState,
    ProjectNotFoundError,
    StateStore,
)


@pytest.fixture
def store():
    """Create an in-memory StateStore."""
    s = StateStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def app(store: StateStore):
    """Create a test FastAPI app with mocked dependencies."""
    app = FastAPI()

    # Override state store dependency
    def override_get_state_store():
        yield store

    app.dependency_overrides[get_state_store] = override_get_state_store

    # Add exception handlers
    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(request: Request, exc: ProjectNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse[None](data=None, error="Project not found").model_dump(),
        )

    @app.exception_handler(PipelineNotFoundError)
    async def pipeline_not_found_handler(request: Request, exc: PipelineNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse[None](data=None, error="Pipeline not found").model_dump(),
        )

    # Include routes
    app.include_router(pipelines.router, prefix="/api/v1")
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
class TestListPipelines:
    """Tests for GET /pipelines."""

    def test_list_pipelines_empty(self, client: TestClient) -> None:
        """Returns empty list when no pipelines."""
        response = client.get("/api/v1/pipelines")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["error"] is None

    def test_list_pipelines_all(self, client: TestClient, store: StateStore, project) -> None:
        """Returns all pipelines."""
        store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )

        response = client.get("/api/v1/pipelines")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    def test_list_pipelines_filter_by_project(self, client: TestClient, store: StateStore) -> None:
        """Filters correctly by project_id."""
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        store.create_pipeline(
            project_id=project1.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        store.create_pipeline(
            project_id=project2.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )

        response = client.get(f"/api/v1/pipelines?project_id={project1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["project_id"] == project1.id

    def test_list_pipelines_filter_by_state(
        self, client: TestClient, store: StateStore, project
    ) -> None:
        """Filters correctly by state."""
        p1 = store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )
        store.update_pipeline(p1.id, state=PipelineState.CODING)

        response = client.get("/api/v1/pipelines?state=coding")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["state"] == "coding"

    def test_list_pipelines_filter_combined(self, client: TestClient, store: StateStore) -> None:
        """Both filters work together."""
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        p1 = store.create_pipeline(
            project_id=project1.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        store.create_pipeline(
            project_id=project1.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )
        store.create_pipeline(
            project_id=project2.id,
            ticket_id="3",
            ticket_title="Ticket 3",
            branch_name="ticket-3",
        )
        store.update_pipeline(p1.id, state=PipelineState.CODING)

        response = client.get(f"/api/v1/pipelines?project_id={project1.id}&state=queued")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["ticket_id"] == "2"


@pytest.mark.unit
class TestGetPipeline:
    """Tests for GET /pipelines/{pipeline_id}."""

    def test_get_pipeline_exists(self, client: TestClient, store: StateStore, project) -> None:
        """200 with pipeline data."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        response = client.get(f"/api/v1/pipelines/{pipeline.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == pipeline.id
        assert data["data"]["ticket_id"] == "42"
        assert data["data"]["ticket_title"] == "Test Ticket"
        assert data["error"] is None

    def test_get_pipeline_not_found(self, client: TestClient) -> None:
        """404 error when pipeline doesn't exist."""
        response = client.get("/api/v1/pipelines/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["data"] is None
        assert "not found" in data["error"].lower()


@pytest.mark.unit
class TestGetPipelineByTicket:
    """Tests for GET /projects/{project_id}/tickets/{ticket_id}/pipeline."""

    def test_get_pipeline_by_ticket_exists(
        self, client: TestClient, store: StateStore, project
    ) -> None:
        """200 with pipeline data."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        response = client.get(f"/api/v1/projects/{project.id}/tickets/42/pipeline")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == pipeline.id
        assert data["data"]["ticket_id"] == "42"
        assert data["error"] is None

    def test_get_pipeline_by_ticket_not_found(self, client: TestClient, project) -> None:
        """404 error when pipeline doesn't exist."""
        response = client.get(f"/api/v1/projects/{project.id}/tickets/999/pipeline")

        assert response.status_code == 404
        data = response.json()
        assert data["data"] is None
        assert "not found" in data["error"].lower()
