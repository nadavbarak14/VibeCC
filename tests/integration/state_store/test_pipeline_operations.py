"""Integration tests for Pipeline operations in StateStore."""

import tempfile
from pathlib import Path

import pytest

from vibecc.state_store import PipelineState, StateStore


@pytest.fixture
def db_path() -> str:
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    # Cleanup
    Path(f.name).unlink(missing_ok=True)
    Path(f"{f.name}-wal").unlink(missing_ok=True)
    Path(f"{f.name}-shm").unlink(missing_ok=True)


@pytest.mark.integration
class TestPipelinePersistence:
    """Tests for pipeline persistence."""

    def test_pipeline_persists_across_reconnect(self, db_path: str) -> None:
        """Pipeline survives DB reconnect."""
        # Create and close
        store1 = StateStore(db_path)
        project = store1.create_project(name="Test", repo="owner/repo")
        pipeline = store1.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )
        pipeline_id = pipeline.id
        store1.close()

        # Reconnect and verify
        store2 = StateStore(db_path)
        loaded = store2.get_pipeline(pipeline_id)
        assert loaded.ticket_id == "42"
        assert loaded.ticket_title == "Test Ticket"
        store2.close()


@pytest.mark.integration
class TestPipelineCrudLifecycle:
    """Tests for full CRUD lifecycle."""

    def test_pipeline_crud_full_lifecycle(self, db_path: str) -> None:
        """Create → Update states → Delete."""
        store = StateStore(db_path)
        project = store.create_project(name="Test", repo="owner/repo")

        # Create
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )
        assert pipeline.state == PipelineState.QUEUED.value

        # Update through state transitions
        store.update_pipeline(pipeline.id, state=PipelineState.CODING)
        pipeline = store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.CODING.value

        store.update_pipeline(pipeline.id, state=PipelineState.TESTING)
        pipeline = store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.TESTING.value

        store.update_pipeline(
            pipeline.id,
            state=PipelineState.REVIEW,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
        )
        pipeline = store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.REVIEW.value
        assert pipeline.pr_id == 123

        store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
        pipeline = store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.MERGED.value

        # Delete
        store.delete_pipeline(pipeline.id)
        pipelines = store.list_pipelines()
        assert len(pipelines) == 0

        store.close()


@pytest.mark.integration
class TestPipelineProjectRelationship:
    """Tests for pipeline-project relationship."""

    def test_pipeline_belongs_to_project(self, db_path: str) -> None:
        """Pipeline correctly linked to project."""
        store = StateStore(db_path)
        project = store.create_project(name="Test", repo="owner/repo")
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        assert pipeline.project_id == project.id

        # Can filter by project
        pipelines = store.list_pipelines(project_id=project.id)
        assert len(pipelines) == 1
        assert pipelines[0].id == pipeline.id

        store.close()

    def test_multiple_pipelines_same_project(self, db_path: str) -> None:
        """Multiple active pipelines per project."""
        store = StateStore(db_path)
        project = store.create_project(name="Test", repo="owner/repo")

        p1 = store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        p2 = store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )
        p3 = store.create_pipeline(
            project_id=project.id,
            ticket_id="3",
            ticket_title="Ticket 3",
            branch_name="ticket-3",
        )

        pipelines = store.list_pipelines(project_id=project.id)
        assert len(pipelines) == 3

        # All have different IDs
        ids = {p.id for p in pipelines}
        assert ids == {p1.id, p2.id, p3.id}

        store.close()

    def test_same_ticket_different_projects(self, db_path: str) -> None:
        """Same ticket_id allowed in different projects."""
        store = StateStore(db_path)
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        # Same ticket_id in different projects should work
        p1 = store.create_pipeline(
            project_id=project1.id,
            ticket_id="42",
            ticket_title="Ticket in Project 1",
            branch_name="ticket-42",
        )
        p2 = store.create_pipeline(
            project_id=project2.id,
            ticket_id="42",
            ticket_title="Ticket in Project 2",
            branch_name="ticket-42",
        )

        assert p1.id != p2.id
        assert p1.project_id == project1.id
        assert p2.project_id == project2.id

        # Can retrieve each by project+ticket
        retrieved1 = store.get_pipeline_by_ticket(project1.id, "42")
        retrieved2 = store.get_pipeline_by_ticket(project2.id, "42")
        assert retrieved1.id == p1.id
        assert retrieved2.id == p2.id

        store.close()
