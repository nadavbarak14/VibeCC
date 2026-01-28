"""Unit tests for project routes."""

import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from vibecc.api.dependencies import get_state_store
from vibecc.api.models import APIResponse
from vibecc.api.routes import projects
from vibecc.state_store import (
    Pipeline,
    PipelineState,
    ProjectExistsError,
    ProjectHasActivePipelinesError,
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

    @app.exception_handler(ProjectExistsError)
    async def project_exists_handler(request: Request, exc: ProjectExistsError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=APIResponse[None](
                data=None, error="Project with this repo already exists"
            ).model_dump(),
        )

    @app.exception_handler(ProjectHasActivePipelinesError)
    async def project_has_pipelines_handler(request: Request, exc: ProjectHasActivePipelinesError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=APIResponse[None](
                data=None, error="Cannot delete project with active pipelines"
            ).model_dump(),
        )

    # Include routes
    app.include_router(projects.router, prefix="/api/v1")

    return app


@pytest.fixture
def client(app: FastAPI):
    """Create a test client."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.unit
class TestListProjects:
    """Tests for GET /projects."""

    def test_list_projects_empty(self, client: TestClient) -> None:
        """Returns empty list when no projects."""
        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["error"] is None

    def test_list_projects_returns_all(self, client: TestClient, store: StateStore) -> None:
        """Returns all projects."""
        # Create some projects
        store.create_project(name="Project A", repo="owner/repo-a")
        store.create_project(name="Project B", repo="owner/repo-b")

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        # Projects are ordered by name
        assert data["data"][0]["name"] == "Project A"
        assert data["data"][1]["name"] == "Project B"


@pytest.mark.unit
class TestCreateProject:
    """Tests for POST /projects."""

    def test_create_project_success(self, client: TestClient) -> None:
        """201 with created project."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "Test Project",
                "repo": "owner/repo",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["error"] is None
        assert data["data"]["name"] == "Test Project"
        assert data["data"]["repo"] == "owner/repo"
        assert data["data"]["base_branch"] == "main"
        assert data["data"]["id"] is not None

    def test_create_project_all_fields(self, client: TestClient) -> None:
        """Creates project with all optional fields."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "Full Project",
                "repo": "owner/full-repo",
                "base_branch": "develop",
                "github_project_id": 12345,
                "max_retries_ci": 5,
                "max_retries_review": 2,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["base_branch"] == "develop"
        assert data["data"]["github_project_id"] == 12345
        assert data["data"]["max_retries_ci"] == 5
        assert data["data"]["max_retries_review"] == 2

    def test_create_project_missing_required_field(self, client: TestClient) -> None:
        """400 error when required field missing."""
        response = client.post(
            "/api/v1/projects",
            json={"name": "Test Project"},  # Missing repo
        )

        assert response.status_code == 422  # Pydantic validation error

    def test_create_project_duplicate_repo(self, client: TestClient, store: StateStore) -> None:
        """409 conflict when repo already exists."""
        store.create_project(name="Existing", repo="owner/repo")

        response = client.post(
            "/api/v1/projects",
            json={"name": "New", "repo": "owner/repo"},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["data"] is None
        assert "already exists" in data["error"]


@pytest.mark.unit
class TestGetProject:
    """Tests for GET /projects/{project_id}."""

    def test_get_project_exists(self, client: TestClient, store: StateStore) -> None:
        """200 with project data."""
        project = store.create_project(name="Test", repo="owner/repo")

        response = client.get(f"/api/v1/projects/{project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == project.id
        assert data["data"]["name"] == "Test"
        assert data["error"] is None

    def test_get_project_not_found(self, client: TestClient) -> None:
        """404 error when project doesn't exist."""
        response = client.get("/api/v1/projects/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert data["data"] is None
        assert "not found" in data["error"].lower()


@pytest.mark.unit
class TestUpdateProject:
    """Tests for PATCH /projects/{project_id}."""

    def test_update_project_success(self, client: TestClient, store: StateStore) -> None:
        """200 with updated project."""
        project = store.create_project(name="Original", repo="owner/repo")

        response = client.patch(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated"
        assert data["data"]["repo"] == "owner/repo"  # Unchanged

    def test_update_project_not_found(self, client: TestClient) -> None:
        """404 error when project doesn't exist."""
        response = client.patch(
            "/api/v1/projects/nonexistent-id",
            json={"name": "Updated"},
        )

        assert response.status_code == 404

    def test_update_project_partial(self, client: TestClient, store: StateStore) -> None:
        """Only updates provided fields."""
        project = store.create_project(
            name="Original",
            repo="owner/repo",
            base_branch="main",
            max_retries_ci=3,
        )

        response = client.patch(
            f"/api/v1/projects/{project.id}",
            json={"max_retries_ci": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Original"  # Unchanged
        assert data["data"]["base_branch"] == "main"  # Unchanged
        assert data["data"]["max_retries_ci"] == 5  # Updated


@pytest.mark.unit
class TestDeleteProject:
    """Tests for DELETE /projects/{project_id}."""

    def test_delete_project_success(self, client: TestClient, store: StateStore) -> None:
        """204 no content on successful delete."""
        project = store.create_project(name="ToDelete", repo="owner/repo")

        response = client.delete(f"/api/v1/projects/{project.id}")

        assert response.status_code == 204

        # Verify project is deleted
        get_response = client.get(f"/api/v1/projects/{project.id}")
        assert get_response.status_code == 404

    def test_delete_project_not_found(self, client: TestClient) -> None:
        """404 error when project doesn't exist."""
        response = client.delete("/api/v1/projects/nonexistent-id")

        assert response.status_code == 404

    def test_delete_project_has_pipelines(self, client: TestClient, store: StateStore) -> None:
        """409 conflict when project has active pipelines."""
        project = store.create_project(name="Test", repo="owner/repo")

        # Create an active pipeline
        session = store._db.get_session()
        pipeline = Pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Active ticket",
            branch_name="ticket-42",
            state=PipelineState.CODING.value,
        )
        session.add(pipeline)
        session.commit()
        session.close()

        response = client.delete(f"/api/v1/projects/{project.id}")

        assert response.status_code == 409
        data = response.json()
        assert "active pipelines" in data["error"].lower()


@pytest.mark.unit
class TestResponseFormat:
    """Tests for consistent response format."""

    def test_response_format_success(self, client: TestClient, store: StateStore) -> None:
        """Success responses have data/error structure."""
        project = store.create_project(name="Test", repo="owner/repo")

        response = client.get(f"/api/v1/projects/{project.id}")

        data = response.json()
        assert "data" in data
        assert "error" in data
        assert data["error"] is None

    def test_response_format_error(self, client: TestClient) -> None:
        """Error responses have data/error structure."""
        response = client.get("/api/v1/projects/nonexistent")

        data = response.json()
        assert "data" in data
        assert "error" in data
        assert data["data"] is None
        assert data["error"] is not None

    def test_response_format_list(self, client: TestClient) -> None:
        """List responses have data/error structure."""
        response = client.get("/api/v1/projects")

        data = response.json()
        assert "data" in data
        assert "error" in data
        assert isinstance(data["data"], list)
