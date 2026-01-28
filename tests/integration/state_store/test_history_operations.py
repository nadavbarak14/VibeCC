"""Integration tests for History operations in StateStore."""

import tempfile
from pathlib import Path

import pytest

from vibecc.state_store import PipelineNotFoundError, PipelineState, StateStore


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
class TestHistoryPersistence:
    """Tests for history persistence."""

    def test_history_persists_across_reconnect(self, db_path: str) -> None:
        """History survives DB reconnect."""
        # Create and close
        store1 = StateStore(db_path)
        project = store1.create_project(name="Test", repo="owner/repo")
        pipeline = store1.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )
        store1.update_pipeline(pipeline.id, state=PipelineState.MERGED)
        pipeline = store1.get_pipeline(pipeline.id)
        history = store1.save_to_history(pipeline)
        history_id = history.id
        store1.close()

        # Reconnect and verify
        store2 = StateStore(db_path)
        loaded_history = store2.get_history()
        assert len(loaded_history) == 1
        assert loaded_history[0].id == history_id
        assert loaded_history[0].ticket_id == "42"
        assert loaded_history[0].ticket_title == "Test Ticket"
        store2.close()


@pytest.mark.integration
class TestPipelineToHistoryFlow:
    """Tests for full pipeline to history flow."""

    def test_full_pipeline_to_history_flow(self, db_path: str) -> None:
        """Create pipeline -> complete -> save to history -> delete pipeline."""
        store = StateStore(db_path)
        project = store.create_project(name="Test", repo="owner/repo")

        # Create pipeline
        pipeline = store.create_pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Test Ticket",
            branch_name="ticket-42",
        )
        assert pipeline.state == PipelineState.QUEUED.value

        # Progress through states
        store.update_pipeline(pipeline.id, state=PipelineState.CODING)
        store.update_pipeline(
            pipeline.id,
            state=PipelineState.TESTING,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
        )
        store.update_pipeline(pipeline.id, state=PipelineState.REVIEW)
        store.update_pipeline(pipeline.id, state=PipelineState.MERGED)

        # Save to history
        pipeline = store.get_pipeline(pipeline.id)
        history = store.save_to_history(pipeline)
        assert history.final_state == PipelineState.MERGED.value
        assert history.pr_id == 123

        # Delete pipeline
        store.delete_pipeline(pipeline.id)

        # Verify pipeline is gone but history remains
        with pytest.raises(PipelineNotFoundError):
            store.get_pipeline(pipeline.id)

        loaded_history = store.get_history()
        assert len(loaded_history) == 1
        assert loaded_history[0].id == history.id

        store.close()


@pytest.mark.integration
class TestHistoryAccumulation:
    """Tests for history accumulation."""

    def test_history_accumulates(self, db_path: str) -> None:
        """Multiple completed pipelines create multiple history records."""
        store = StateStore(db_path)
        project = store.create_project(name="Test", repo="owner/repo")

        history_ids = []
        for i in range(5):
            pipeline = store.create_pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Ticket {i}",
                branch_name=f"ticket-{i}",
            )
            store.update_pipeline(pipeline.id, state=PipelineState.MERGED)
            pipeline = store.get_pipeline(pipeline.id)
            history = store.save_to_history(pipeline)
            history_ids.append(history.id)
            store.delete_pipeline(pipeline.id)

        # All history records should exist
        loaded_history = store.get_history()
        assert len(loaded_history) == 5

        loaded_ids = {h.id for h in loaded_history}
        assert loaded_ids == set(history_ids)

        store.close()

    def test_history_stats_updates(self, db_path: str) -> None:
        """Stats reflect new history entries."""
        store = StateStore(db_path)
        project = store.create_project(name="Test", repo="owner/repo")

        # Initial stats should be empty
        stats = store.get_history_stats()
        assert stats.total_completed == 0

        # Add first entry
        p1 = store.create_pipeline(
            project_id=project.id,
            ticket_id="1",
            ticket_title="Ticket 1",
            branch_name="ticket-1",
        )
        store.update_pipeline(p1.id, state=PipelineState.MERGED, retry_count_ci=2)
        p1 = store.get_pipeline(p1.id)
        store.save_to_history(p1)

        stats = store.get_history_stats()
        assert stats.total_completed == 1
        assert stats.total_merged == 1
        assert stats.total_failed == 0
        assert stats.avg_retries_ci == 2.0

        # Add second entry (failed)
        p2 = store.create_pipeline(
            project_id=project.id,
            ticket_id="2",
            ticket_title="Ticket 2",
            branch_name="ticket-2",
        )
        store.update_pipeline(p2.id, state=PipelineState.FAILED, retry_count_ci=4)
        p2 = store.get_pipeline(p2.id)
        store.save_to_history(p2)

        stats = store.get_history_stats()
        assert stats.total_completed == 2
        assert stats.total_merged == 1
        assert stats.total_failed == 1
        # Average CI retries: (2 + 4) / 2 = 3.0
        assert stats.avg_retries_ci == 3.0

        store.close()
