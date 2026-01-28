"""Unit tests for history routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vibecc.api.dependencies import get_state_store
from vibecc.api.routes import history
from vibecc.state_store import (
    PipelineState,
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

    # Include routes
    app.include_router(history.router, prefix="/api/v1")

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


def create_history_entry(store: StateStore, project, ticket_id: str, state: PipelineState):
    """Helper to create a history entry."""
    pipeline = store.create_pipeline(
        project_id=project.id,
        ticket_id=ticket_id,
        ticket_title=f"Ticket {ticket_id}",
        branch_name=f"ticket-{ticket_id}",
    )
    store.update_pipeline(pipeline.id, state=state)
    pipeline = store.get_pipeline(pipeline.id)
    return store.save_to_history(pipeline)


@pytest.mark.unit
class TestListHistory:
    """Tests for GET /history."""

    def test_list_history_empty(self, client: TestClient) -> None:
        """Returns empty list when no history."""
        response = client.get("/api/v1/history")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["error"] is None

    def test_list_history_all(self, client: TestClient, store: StateStore, project) -> None:
        """Returns all history entries."""
        create_history_entry(store, project, "1", PipelineState.MERGED)
        create_history_entry(store, project, "2", PipelineState.MERGED)
        create_history_entry(store, project, "3", PipelineState.FAILED)

        response = client.get("/api/v1/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    def test_list_history_filter_by_project(self, client: TestClient, store: StateStore) -> None:
        """Filters correctly by project_id."""
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        create_history_entry(store, project1, "1", PipelineState.MERGED)
        create_history_entry(store, project1, "2", PipelineState.MERGED)
        create_history_entry(store, project2, "3", PipelineState.MERGED)

        response = client.get(f"/api/v1/history?project_id={project1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert all(h["project_id"] == project1.id for h in data["data"])

    def test_list_history_filter_by_final_state(
        self, client: TestClient, store: StateStore, project
    ) -> None:
        """Filters correctly by final_state."""
        create_history_entry(store, project, "1", PipelineState.MERGED)
        create_history_entry(store, project, "2", PipelineState.MERGED)
        create_history_entry(store, project, "3", PipelineState.FAILED)

        response = client.get("/api/v1/history?final_state=merged")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert all(h["final_state"] == "merged" for h in data["data"])

    def test_list_history_pagination_limit(
        self, client: TestClient, store: StateStore, project
    ) -> None:
        """Respects limit parameter."""
        for i in range(5):
            create_history_entry(store, project, str(i), PipelineState.MERGED)

        response = client.get("/api/v1/history?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3

    def test_list_history_pagination_offset(
        self, client: TestClient, store: StateStore, project
    ) -> None:
        """Respects offset parameter."""
        for i in range(5):
            create_history_entry(store, project, str(i), PipelineState.MERGED)

        # Get all first
        all_response = client.get("/api/v1/history")
        all_data = all_response.json()

        # Get with offset
        response = client.get("/api/v1/history?offset=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        # Should skip first 2
        assert data["data"][0]["id"] == all_data["data"][2]["id"]


@pytest.mark.unit
class TestGetHistoryStats:
    """Tests for GET /history/stats."""

    def test_get_history_stats_empty(self, client: TestClient) -> None:
        """Returns zeros when no history."""
        response = client.get("/api/v1/history/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_completed"] == 0
        assert data["data"]["total_merged"] == 0
        assert data["data"]["total_failed"] == 0
        assert data["data"]["avg_duration_seconds"] == 0.0
        assert data["data"]["avg_retries_ci"] == 0.0
        assert data["data"]["avg_retries_review"] == 0.0
        assert data["error"] is None

    def test_get_history_stats_calculated(
        self, client: TestClient, store: StateStore, project
    ) -> None:
        """Returns correct stats."""
        # Create 2 merged, 1 failed with known retry counts
        p1 = store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        store.update_pipeline(p1.id, state=PipelineState.MERGED, retry_count_ci=2)
        p1 = store.get_pipeline(p1.id)
        store.save_to_history(p1)

        p2 = store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )
        store.update_pipeline(p2.id, state=PipelineState.MERGED, retry_count_ci=4)
        p2 = store.get_pipeline(p2.id)
        store.save_to_history(p2)

        p3 = store.create_pipeline(
            project_id=project.id,
            ticket_id="3",
            ticket_title="Ticket 3",
            branch_name="ticket-3",
        )
        store.update_pipeline(p3.id, state=PipelineState.FAILED, retry_count_ci=0)
        p3 = store.get_pipeline(p3.id)
        store.save_to_history(p3)

        response = client.get("/api/v1/history/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_completed"] == 3
        assert data["data"]["total_merged"] == 2
        assert data["data"]["total_failed"] == 1
        # Average CI retries: (2 + 4 + 0) / 3 = 2.0
        assert data["data"]["avg_retries_ci"] == pytest.approx(2.0)

    def test_get_history_stats_filter_by_project(
        self, client: TestClient, store: StateStore
    ) -> None:
        """Filters correctly by project_id."""
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        create_history_entry(store, project1, "1", PipelineState.MERGED)
        create_history_entry(store, project1, "2", PipelineState.MERGED)
        create_history_entry(store, project2, "3", PipelineState.MERGED)

        response = client.get(f"/api/v1/history/stats?project_id={project1.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_completed"] == 2
