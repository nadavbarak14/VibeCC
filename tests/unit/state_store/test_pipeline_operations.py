"""Unit tests for Pipeline operations in StateStore."""

import time

import pytest

from vibecc.state_store import (
    PipelineExistsError,
    PipelineNotFoundError,
    PipelineState,
    ProjectNotFoundError,
    StateStore,
)


@pytest.fixture
def store() -> StateStore:
    """Create an in-memory StateStore."""
    s = StateStore(":memory:")
    yield s
    s.close()


@pytest.fixture
def project(store: StateStore):
    """Create a test project."""
    return store.create_project(name="Test Project", repo="owner/repo")


@pytest.mark.unit
class TestCreatePipeline:
    """Tests for create_pipeline."""

    def test_create_pipeline_success(self, store: StateStore, project) -> None:
        """Create pipeline with all required fields."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
            ticket_body="Test body",
        )

        assert pipeline.id is not None
        assert pipeline.project_id == project.id
        assert pipeline.ticket_id == "42"
        assert pipeline.ticket_title == "Test Ticket"
        assert pipeline.branch_name == "ticket-42"
        assert pipeline.ticket_body == "Test body"

    def test_create_pipeline_initial_state_queued(self, store: StateStore, project) -> None:
        """New pipeline starts in QUEUED."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        assert pipeline.state == PipelineState.QUEUED.value
        assert pipeline.pipeline_state == PipelineState.QUEUED

    def test_create_pipeline_initial_retry_counts_zero(self, store: StateStore, project) -> None:
        """Retry counts start at 0."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        assert pipeline.retry_count_ci == 0
        assert pipeline.retry_count_review == 0

    def test_create_pipeline_invalid_project_raises(self, store: StateStore) -> None:
        """ProjectNotFoundError for bad project_id."""
        with pytest.raises(ProjectNotFoundError):
            store.create_pipeline(
                project_id="nonexistent",
                ticket_id="42",
                ticket_title="Test Ticket",
                branch_name="ticket-42",
            )

    def test_create_pipeline_duplicate_ticket_raises(self, store: StateStore, project) -> None:
        """PipelineExistsError for same project+ticket."""
        store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        with pytest.raises(PipelineExistsError):
            store.create_pipeline(
                project_id=project.id,
                ticket_id="42",
                ticket_title="Another Ticket",
                branch_name="ticket-42-v2",
            )


@pytest.mark.unit
class TestGetPipeline:
    """Tests for get_pipeline."""

    def test_get_pipeline_exists(self, store: StateStore, project) -> None:
        """Returns correct pipeline."""
        created = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        pipeline = store.get_pipeline(created.id)

        assert pipeline.id == created.id
        assert pipeline.ticket_id == "42"

    def test_get_pipeline_not_found_raises(self, store: StateStore) -> None:
        """PipelineNotFoundError for invalid ID."""
        with pytest.raises(PipelineNotFoundError):
            store.get_pipeline("nonexistent")


@pytest.mark.unit
class TestGetPipelineByTicket:
    """Tests for get_pipeline_by_ticket."""

    def test_get_pipeline_by_ticket_exists(self, store: StateStore, project) -> None:
        """Returns correct pipeline by project+ticket."""
        created = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        pipeline = store.get_pipeline_by_ticket(project.id, "42")

        assert pipeline.id == created.id
        assert pipeline.ticket_id == "42"

    def test_get_pipeline_by_ticket_not_found_raises(self, store: StateStore, project) -> None:
        """PipelineNotFoundError for nonexistent ticket."""
        with pytest.raises(PipelineNotFoundError):
            store.get_pipeline_by_ticket(project.id, "nonexistent")


@pytest.mark.unit
class TestListPipelines:
    """Tests for list_pipelines."""

    def test_list_pipelines_all(self, store: StateStore, project) -> None:
        """Returns all pipelines when no filters."""
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

        pipelines = store.list_pipelines()

        assert len(pipelines) == 2

    def test_list_pipelines_by_project(self, store: StateStore) -> None:
        """Filters by project_id correctly."""
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

        pipelines = store.list_pipelines(project_id=project1.id)

        assert len(pipelines) == 1
        assert pipelines[0].project_id == project1.id

    def test_list_pipelines_by_state(self, store: StateStore, project) -> None:
        """Filters by state correctly."""
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

        # Update one to CODING
        store.update_pipeline(p1.id, state=PipelineState.CODING)

        pipelines = store.list_pipelines(state=PipelineState.QUEUED)

        assert len(pipelines) == 1
        assert pipelines[0].state == PipelineState.QUEUED.value

    def test_list_pipelines_by_project_and_state(self, store: StateStore) -> None:
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

        # Update p1 to CODING
        store.update_pipeline(p1.id, state=PipelineState.CODING)

        pipelines = store.list_pipelines(project_id=project1.id, state=PipelineState.QUEUED)

        assert len(pipelines) == 1
        assert pipelines[0].ticket_id == "2"

    def test_list_pipelines_ordered_by_created_at(self, store: StateStore, project) -> None:
        """Most recent first."""
        store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="First",
            branch_name="ticket-1",
        )
        time.sleep(1.1)  # SQLite timestamp resolution is 1 second
        store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Second",
            branch_name="ticket-2",
        )

        pipelines = store.list_pipelines()

        assert pipelines[0].ticket_id == "2"  # Most recent first
        assert pipelines[1].ticket_id == "1"


@pytest.mark.unit
class TestUpdatePipeline:
    """Tests for update_pipeline."""

    def test_update_pipeline_state(self, store: StateStore, project) -> None:
        """Update state field."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        updated = store.update_pipeline(pipeline.id, state=PipelineState.CODING)

        assert updated.state == PipelineState.CODING.value

    def test_update_pipeline_pr_fields(self, store: StateStore, project) -> None:
        """Update pr_id and pr_url."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        updated = store.update_pipeline(
            pipeline.id,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
        )

        assert updated.pr_id == 123
        assert updated.pr_url == "https://github.com/owner/repo/pull/123"

    def test_update_pipeline_retry_counts(self, store: StateStore, project) -> None:
        """Update retry counts."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        updated = store.update_pipeline(
            pipeline.id,
            retry_count_ci=2,
            retry_count_review=1,
        )

        assert updated.retry_count_ci == 2
        assert updated.retry_count_review == 1

    def test_update_pipeline_feedback(self, store: StateStore, project) -> None:
        """Update feedback field."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        updated = store.update_pipeline(pipeline.id, feedback="CI failed: test_foo")

        assert updated.feedback == "CI failed: test_foo"

    def test_update_pipeline_not_found_raises(self, store: StateStore) -> None:
        """PipelineNotFoundError for invalid ID."""
        with pytest.raises(PipelineNotFoundError):
            store.update_pipeline("nonexistent", state=PipelineState.CODING)

    def test_update_pipeline_sets_updated_at(self, store: StateStore, project) -> None:
        """updated_at timestamp changes."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )
        original_updated_at = pipeline.updated_at

        time.sleep(1.1)  # SQLite timestamp resolution is 1 second
        updated = store.update_pipeline(pipeline.id, state=PipelineState.CODING)

        assert updated.updated_at > original_updated_at


@pytest.mark.unit
class TestDeletePipeline:
    """Tests for delete_pipeline."""

    def test_delete_pipeline_exists(self, store: StateStore, project) -> None:
        """Successfully deletes."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )

        store.delete_pipeline(pipeline.id)

        with pytest.raises(PipelineNotFoundError):
            store.get_pipeline(pipeline.id)

    def test_delete_pipeline_not_found_raises(self, store: StateStore) -> None:
        """PipelineNotFoundError for invalid ID."""
        with pytest.raises(PipelineNotFoundError):
            store.delete_pipeline("nonexistent")
