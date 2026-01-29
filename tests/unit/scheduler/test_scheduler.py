"""Unit tests for Scheduler."""

from unittest.mock import MagicMock

import pytest

from vibecc.kanban import Ticket
from vibecc.scheduler import Scheduler, SyncResult
from vibecc.state_store import PipelineState


@pytest.fixture
def mock_state_store() -> MagicMock:
    """Create a mock StateStore."""
    store = MagicMock()
    store.list_pipelines.return_value = []
    return store


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create a mock Orchestrator."""
    return MagicMock()


@pytest.fixture
def mock_kanban() -> MagicMock:
    """Create a mock KanbanAdapter."""
    return MagicMock()


@pytest.fixture
def mock_git_manager() -> MagicMock:
    """Create a mock GitManager."""
    return MagicMock()


@pytest.fixture
def sample_tickets() -> list[Ticket]:
    """Create sample tickets."""
    return [
        Ticket(id="1", title="Add login", body="Implement login", labels=[]),
        Ticket(id="2", title="Fix bug", body="Fix navbar", labels=[]),
        Ticket(id="3", title="Add search", body="Full-text search", labels=[]),
    ]


@pytest.fixture
def scheduler(mock_state_store: MagicMock, mock_orchestrator: MagicMock) -> Scheduler:
    """Create a Scheduler with max_concurrent=2."""
    return Scheduler(
        state_store=mock_state_store,
        orchestrator=mock_orchestrator,
        max_concurrent=2,
    )


@pytest.mark.unit
class TestSyncPullsFromQueue:
    """Test that sync queries the kanban queue."""

    def test_sync_pulls_from_queue(
        self,
        scheduler: Scheduler,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
    ) -> None:
        """Kanban queried for tickets in queue."""
        mock_kanban.list_tickets.return_value = []

        scheduler.sync("project-1", mock_kanban, mock_git_manager)

        mock_kanban.list_tickets.assert_called_once_with("queue")


@pytest.mark.unit
class TestSyncPullsAllTickets:
    """Test that sync pulls all tickets into queue (unlimited queue model)."""

    def test_sync_pulls_all_tickets(
        self,
        scheduler: Scheduler,
        mock_state_store: MagicMock,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """All tickets pulled into queue regardless of working pipeline count."""
        mock_kanban.list_tickets.return_value = sample_tickets  # 3 tickets

        # Even with 1 active pipeline, all tickets should be pulled into queue
        def list_pipelines_side_effect(project_id: str, state: PipelineState) -> list:
            if state == PipelineState.CODING:
                return [MagicMock()]
            return []

        mock_state_store.list_pipelines.side_effect = list_pipelines_side_effect

        pipeline_mock = MagicMock()
        mock_orchestrator.start_pipeline.return_value = pipeline_mock

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        # All tickets pulled into queue (unlimited queue model)
        assert mock_orchestrator.start_pipeline.call_count == 3
        assert len(result.started) == 3
        assert result.remaining == 0


@pytest.mark.unit
class TestSyncStartsPipelines:
    """Test that sync starts pipelines via orchestrator."""

    def test_sync_starts_pipelines(
        self,
        scheduler: Scheduler,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """Orchestrator called for each ticket up to capacity."""
        mock_kanban.list_tickets.return_value = sample_tickets[:2]

        pipeline1 = MagicMock()
        pipeline2 = MagicMock()
        mock_orchestrator.start_pipeline.side_effect = [pipeline1, pipeline2]

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert mock_orchestrator.start_pipeline.call_count == 2
        mock_orchestrator.start_pipeline.assert_any_call(
            "project-1", sample_tickets[0], mock_git_manager
        )
        mock_orchestrator.start_pipeline.assert_any_call(
            "project-1", sample_tickets[1], mock_git_manager
        )
        assert result.started == [pipeline1, pipeline2]


@pytest.mark.unit
class TestSyncMovesTickets:
    """Test that sync moves started tickets to in_progress."""

    def test_sync_moves_tickets(
        self,
        scheduler: Scheduler,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """Tickets moved to in_progress after pipeline started."""
        mock_kanban.list_tickets.return_value = sample_tickets[:2]
        mock_orchestrator.start_pipeline.return_value = MagicMock()

        scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert mock_kanban.move_ticket.call_count == 2
        mock_kanban.move_ticket.assert_any_call("1", "in_progress")
        mock_kanban.move_ticket.assert_any_call("2", "in_progress")


@pytest.mark.unit
class TestSyncReturnsResult:
    """Test that sync returns correct SyncResult."""

    def test_sync_returns_result(
        self,
        scheduler: Scheduler,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """Started count and remaining are correct."""
        mock_kanban.list_tickets.return_value = sample_tickets  # 3 tickets
        pipeline1 = MagicMock()
        pipeline2 = MagicMock()
        pipeline3 = MagicMock()
        mock_orchestrator.start_pipeline.side_effect = [pipeline1, pipeline2, pipeline3]

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert isinstance(result, SyncResult)
        # All tickets pulled into queue (unlimited queue model)
        assert len(result.started) == 3
        assert result.remaining == 0


@pytest.mark.unit
class TestSyncEmptyQueue:
    """Test sync with empty queue."""

    def test_sync_empty_queue(
        self,
        scheduler: Scheduler,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
    ) -> None:
        """Returns empty started list when queue is empty."""
        mock_kanban.list_tickets.return_value = []

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert result.started == []
        assert result.remaining == 0
        mock_orchestrator.start_pipeline.assert_not_called()


@pytest.mark.unit
class TestSyncAtMaxCapacity:
    """Test sync when at max capacity (still pulls all tickets)."""

    def test_sync_at_max_capacity_still_queues(
        self,
        scheduler: Scheduler,
        mock_state_store: MagicMock,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """All tickets still pulled into queue even when at max capacity.

        The unlimited queue model means sync always pulls all tickets.
        max_concurrent only affects when pipelines start processing.
        """
        mock_kanban.list_tickets.return_value = sample_tickets  # 3 tickets

        # Even with 2 active pipelines = max_concurrent, tickets are still pulled
        def list_pipelines_side_effect(project_id: str, state: PipelineState) -> list:
            if state == PipelineState.CODING:
                return [MagicMock()]
            if state == PipelineState.TESTING:
                return [MagicMock()]
            return []

        mock_state_store.list_pipelines.side_effect = list_pipelines_side_effect
        mock_orchestrator.start_pipeline.return_value = MagicMock()

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        # All tickets pulled into QUEUED state
        assert len(result.started) == 3
        assert result.remaining == 0
        assert mock_orchestrator.start_pipeline.call_count == 3
