"""Integration tests for project routes."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibecc.api.app import create_app
from vibecc.api.dependencies import close_state_store, init_state_store


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def client(temp_db_path: str):
    """Create a test client with temporary database."""
    init_state_store(temp_db_path)
    app = create_app(temp_db_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    close_state_store()
    # Cleanup
    Path(temp_db_path).unlink(missing_ok=True)
    Path(f"{temp_db_path}-wal").unlink(missing_ok=True)
    Path(f"{temp_db_path}-shm").unlink(missing_ok=True)


@pytest.mark.integration
class TestProjectCrudFullFlow:
    """Integration test for full CRUD flow."""

    def test_project_crud_full_flow(self, client: TestClient) -> None:
        """Create -> Read -> Update -> Delete flow."""
        # 1. Create
        create_response = client.post(
            "/api/v1/projects",
            json={
                "name": "Test Project",
                "repo": "owner/test-repo",
                "base_branch": "main",
            },
        )
        assert create_response.status_code == 201
        project_id = create_response.json()["data"]["id"]

        # 2. Read
        get_response = client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["data"]["name"] == "Test Project"

        # 3. Update
        update_response = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "Updated Project", "max_retries_ci": 5},
        )
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "Updated Project"
        assert update_response.json()["data"]["max_retries_ci"] == 5

        # Verify update persisted
        get_response2 = client.get(f"/api/v1/projects/{project_id}")
        assert get_response2.json()["data"]["name"] == "Updated Project"

        # 4. Delete
        delete_response = client.delete(f"/api/v1/projects/{project_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        get_response3 = client.get(f"/api/v1/projects/{project_id}")
        assert get_response3.status_code == 404


@pytest.mark.integration
class TestOpenAPIDocs:
    """Integration test for OpenAPI documentation."""

    def test_openapi_docs_available(self, client: TestClient) -> None:
        """/docs returns 200."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient) -> None:
        """/redoc returns 200."""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json_available(self, client: TestClient) -> None:
        """/openapi.json returns valid OpenAPI spec."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "/api/v1/projects" in data["paths"]
