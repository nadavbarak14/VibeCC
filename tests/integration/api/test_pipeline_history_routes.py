"""Integration tests for pipeline and history routes."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibecc.api.app import create_app
from vibecc.api.dependencies import close_state_store, init_state_store
from vibecc.state_store import PipelineState, StateStore


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
def app(db_path: str):
    """Create the FastAPI app with real database."""
    app = create_app(db_path)
    init_state_store(db_path)
    yield app
    close_state_store()


@pytest.fixture
def client(app):
    """Create a test client."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def store(db_path: str):
    """Get a StateStore instance for direct DB access."""
    return StateStore(db_path)


@pytest.mark.integration
class TestPipelineAppears:
    """Tests for pipeline appearing after creation."""

    def test_pipeline_appears_after_creation(self, client: TestClient, store: StateStore) -> None:
        """Created pipeline shows in list."""
        # Create a project first
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "repo": "owner/test-repo"},
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # Pipelines list should be empty initially
        list_response = client.get("/api/v1/pipelines")
        assert list_response.status_code == 200
        assert list_response.json()["data"] == []

        # Create a pipeline directly in the store
        pipeline = store.create_pipeline(
            project_id=project_id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        # Pipeline should now appear in the list
        list_response = client.get("/api/v1/pipelines")
        assert list_response.status_code == 200
        data = list_response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == pipeline.id
        assert data[0]["ticket_id"] == "42"

        # Pipeline should be retrievable by ID
        get_response = client.get(f"/api/v1/pipelines/{pipeline.id}")
        assert get_response.status_code == 200
        assert get_response.json()["data"]["id"] == pipeline.id

        # Pipeline should be retrievable by ticket
        ticket_response = client.get(f"/api/v1/projects/{project_id}/tickets/42/pipeline")
        assert ticket_response.status_code == 200
        assert ticket_response.json()["data"]["id"] == pipeline.id


@pytest.mark.integration
class TestHistoryAppears:
    """Tests for history appearing after pipeline completion."""

    def test_history_appears_after_completion(self, client: TestClient, store: StateStore) -> None:
        """Completed pipeline shows in history."""
        # Create a project first
        project_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Project", "repo": "owner/test-repo"},
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["data"]["id"]

        # History should be empty initially
        history_response = client.get("/api/v1/history")
        assert history_response.status_code == 200
        assert history_response.json()["data"] == []

        # Stats should show zeros
        stats_response = client.get("/api/v1/history/stats")
        assert stats_response.status_code == 200
        assert stats_response.json()["data"]["total_completed"] == 0

        # Create and complete a pipeline
        pipeline = store.create_pipeline(
            project_id=project_id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )
        store.update_pipeline(
            pipeline.id,
            state=PipelineState.MERGED,
            pr_id=123,
            pr_url="https://github.com/owner/test-repo/pull/123",
        )
        pipeline = store.get_pipeline(pipeline.id)
        store.save_to_history(pipeline)

        # History should now have the entry
        history_response = client.get("/api/v1/history")
        assert history_response.status_code == 200
        history_data = history_response.json()["data"]
        assert len(history_data) == 1
        assert history_data[0]["ticket_id"] == "42"
        assert history_data[0]["final_state"] == "merged"
        assert history_data[0]["pr_id"] == 123

        # Stats should reflect the entry
        stats_response = client.get("/api/v1/history/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()["data"]
        assert stats_data["total_completed"] == 1
        assert stats_data["total_merged"] == 1
        assert stats_data["total_failed"] == 0
