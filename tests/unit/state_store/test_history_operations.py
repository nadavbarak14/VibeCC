"""Unit tests for History operations in StateStore."""

import time

import pytest

from vibecc.state_store import (
    PipelineState,
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


@pytest.fixture
def completed_pipeline(store: StateStore, project):
    """Create a completed (MERGED) pipeline."""
    pipeline = store.create_pipeline(
        project_id=project.id,
        ticket_id="42",
        ticket_title="Test Ticket",
        branch_name="ticket-42",
        ticket_body="Test body",
    )
    store.update_pipeline(
        pipeline.id,
        state=PipelineState.MERGED,
        pr_id=123,
        pr_url="https://github.com/owner/repo/pull/123",
        retry_count_ci=2,
        retry_count_review=1,
    )
    return store.get_pipeline(pipeline.id)


@pytest.mark.unit
class TestSaveToHistory:
    """Tests for save_to_history."""

    def test_save_to_history_copies_all_fields(self, store: StateStore, completed_pipeline) -> None:
        """All pipeline fields copied correctly."""
        history = store.save_to_history(completed_pipeline)

        assert history.id is not None
        assert history.project_id == completed_pipeline.project_id
        assert history.ticket_id == completed_pipeline.ticket_id
        assert history.ticket_title == completed_pipeline.ticket_title
        assert history.final_state == completed_pipeline.state
        assert history.branch_name == completed_pipeline.branch_name
        assert history.pr_id == completed_pipeline.pr_id
        assert history.pr_url == completed_pipeline.pr_url
        assert history.total_retries_ci == completed_pipeline.retry_count_ci
        assert history.total_retries_review == completed_pipeline.retry_count_review
        assert history.started_at == completed_pipeline.created_at

    def test_save_to_history_sets_completed_at(self, store: StateStore, completed_pipeline) -> None:
        """completed_at timestamp set."""
        history = store.save_to_history(completed_pipeline)

        assert history.completed_at is not None
        assert history.completed_at >= completed_pipeline.created_at

    def test_save_to_history_calculates_duration(self, store: StateStore, project) -> None:
        """duration_seconds calculated from timestamps."""
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="99",
            ticket_title="Duration Test",
            branch_name="ticket-99",
        )
        # Wait to ensure measurable duration
        time.sleep(1.1)

        store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
        pipeline = store.get_pipeline(pipeline.id)
        history = store.save_to_history(pipeline)

        assert history.duration_seconds >= 1

    def test_save_to_history_does_not_delete_pipeline(
        self, store: StateStore, completed_pipeline
    ) -> None:
        """Original pipeline still exists after save."""
        store.save_to_history(completed_pipeline)

        # Pipeline should still exist
        pipeline = store.get_pipeline(completed_pipeline.id)
        assert pipeline is not None
        assert pipeline.id == completed_pipeline.id


@pytest.mark.unit
class TestGetHistory:
    """Tests for get_history."""

    def test_get_history_empty(self, store: StateStore) -> None:
        """Returns empty list when no history."""
        history = store.get_history()

        assert history == []

    def test_get_history_all(self, store: StateStore, project) -> None:
        """Returns all history entries."""
        # Create and save multiple pipelines to history
        for i in range(3):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)

        history = store.get_history()

        assert len(history) == 3

    def test_get_history_by_project(self, store: StateStore) -> None:
        """Filters by project_id."""
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        # Add history entries for both projects
        for proj, ticket_id in [(project1, "1"), (project1, "2"), (project2, "3")]:
            pipeline = store.create_pipeline(
                project_id=proj.id,
                ticket_id=ticket_id,
                ticket_title=f"Ticket {ticket_id}",
                branch_name=f"ticket-{ticket_id}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)

        history = store.get_history(project_id=project1.id)

        assert len(history) == 2
        assert all(h.project_id == project1.id for h in history)

    def test_get_history_by_final_state(self, store: StateStore, project) -> None:
        """Filters by MERGED or FAILED."""
        # Create merged pipeline
        p1 = store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="Merged Ticket",
            branch_name="ticket-1",
        )
        store.update_pipeline(p1.id, state=PipelineState.MERGED)
        p1 = store.get_pipeline(p1.id)
        store.save_to_history(p1)

        # Create failed pipeline
        p2 = store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Failed Ticket",
            branch_name="ticket-2",
        )
        store.update_pipeline(p2.id, state=PipelineState.FAILED)
        p2 = store.get_pipeline(p2.id)
        store.save_to_history(p2)

        merged_history = store.get_history(final_state=PipelineState.MERGED)
        failed_history = store.get_history(final_state=PipelineState.FAILED)

        assert len(merged_history) == 1
        assert merged_history[0].final_state == PipelineState.MERGED.value
        assert len(failed_history) == 1
        assert failed_history[0].final_state == PipelineState.FAILED.value

    def test_get_history_pagination_limit(self, store: StateStore, project) -> None:
        """Respects limit parameter."""
        # Create 5 history entries
        for i in range(5):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)

        history = store.get_history(limit=3)

        assert len(history) == 3

    def test_get_history_pagination_offset(self, store: StateStore, project) -> None:
        """Respects offset parameter."""
        # Create 5 history entries with delays for ordering
        for i in range(5):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)
            time.sleep(0.1)

        # Get all first
        all_history = store.get_history()
        # Get with offset
        offset_history = store.get_history(offset=2)

        assert len(offset_history) == 3
        # Should skip first 2 (most recent)
        assert offset_history[0].id == all_history[2].id

    def test_get_history_ordered_by_completed_at(self, store: StateStore, project) -> None:
        """Most recent first."""
        # Create entries with delays to ensure different timestamps
        for i in range(3):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)
            time.sleep(1.1)  # SQLite timestamp resolution is 1 second

        history = store.get_history()

        # Most recent first (highest ticket_id was created last)
        assert history[0].ticket_id == "2"
        assert history[1].ticket_id == "1"
        assert history[2].ticket_id == "0"


@pytest.mark.unit
class TestGetHistoryStats:
    """Tests for get_history_stats."""

    def test_get_history_stats_empty(self, store: StateStore) -> None:
        """Returns zeros when no history."""
        stats = store.get_history_stats()

        assert stats.total_completed == 0
        assert stats.total_merged == 0
        assert stats.total_failed == 0
        assert stats.avg_duration_seconds == 0.0
        assert stats.avg_retries_ci == 0.0
        assert stats.avg_retries_review == 0.0

    def test_get_history_stats_counts(self, store: StateStore, project) -> None:
        """Correct total/merged/failed counts."""
        # Create 2 merged and 1 failed
        for i, state in enumerate(
            [PipelineState.MERGED, PipelineState.MERGED, PipelineState.FAILED]
        ):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(pipeline.id, state=state)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)

        stats = store.get_history_stats()

        assert stats.total_completed == 3
        assert stats.total_merged == 2
        assert stats.total_failed == 1

    def test_get_history_stats_averages(self, store: StateStore, project) -> None:
        """Correct avg duration and retries."""
        # Create pipelines with known retry counts
        retry_configs = [
            (2, 1),  # ci=2, review=1
            (4, 3),  # ci=4, review=3
            (0, 2),  # ci=0, review=2
        ]
        for i, (ci_retries, review_retries) in enumerate(retry_configs):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(
                pipeline.id,
                state=PipelineState.MERGED,
                retry_count_ci=ci_retries,
                retry_count_review=review_retries,
            )
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)

        stats = store.get_history_stats()

        # Average CI retries: (2 + 4 + 0) / 3 = 2.0
        assert stats.avg_retries_ci == pytest.approx(2.0)
        # Average review retries: (1 + 3 + 2) / 3 = 2.0
        assert stats.avg_retries_review == pytest.approx(2.0)
        # Duration should be non-negative
        assert stats.avg_duration_seconds >= 0

    def test_get_history_stats_by_project(self, store: StateStore) -> None:
        """Filters stats by project."""
        project1 = store.create_project(name="Project 1", repo="owner/repo1")
        project2 = store.create_project(name="Project 2", repo="owner/repo2")

        # Add 2 to project1, 1 to project2
        for proj, ticket_id in [(project1, "1"), (project1, "2"), (project2, "3")]:
            pipeline = store.create_pipeline(
                project_id=proj.id,
                ticket_id=ticket_id,
                ticket_title=f"Ticket {ticket_id}",
                branch_name=f"ticket-{ticket_id}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            store.save_to_history(pipeline)

        stats1 = store.get_history_stats(project_id=project1.id)
        stats2 = store.get_history_stats(project_id=project2.id)

        assert stats1.total_completed == 2
        assert stats2.total_completed == 1
