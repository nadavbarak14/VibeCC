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
class TestSyncRespectsCapacity:
    """Test that sync respects concurrency limits."""

    def test_sync_respects_capacity(
        self,
        scheduler: Scheduler,
        mock_state_store: MagicMock,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """Only starts up to available capacity."""
        mock_kanban.list_tickets.return_value = sample_tickets

        # 1 active pipeline (CODING), so only 1 slot available (max_concurrent=2)
        def list_pipelines_side_effect(project_id: str, state: PipelineState) -> list:
            if state == PipelineState.CODING:
                return [MagicMock()]
            return []

        mock_state_store.list_pipelines.side_effect = list_pipelines_side_effect

        pipeline_mock = MagicMock()
        mock_orchestrator.start_pipeline.return_value = pipeline_mock

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert mock_orchestrator.start_pipeline.call_count == 1
        assert len(result.started) == 1
        assert result.remaining == 2


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
        mock_orchestrator.start_pipeline.side_effect = [pipeline1, pipeline2]

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert isinstance(result, SyncResult)
        assert len(result.started) == 2  # max_concurrent=2
        assert result.remaining == 1  # 3 - 2 = 1


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
class TestSyncNoCapacity:
    """Test sync when no capacity available."""

    def test_sync_no_capacity(
        self,
        scheduler: Scheduler,
        mock_state_store: MagicMock,
        mock_orchestrator: MagicMock,
        mock_kanban: MagicMock,
        mock_git_manager: MagicMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """Returns zero started when at max capacity."""
        mock_kanban.list_tickets.return_value = sample_tickets

        # 2 active pipelines = max_concurrent, so no capacity
        def list_pipelines_side_effect(project_id: str, state: PipelineState) -> list:
            if state == PipelineState.CODING:
                return [MagicMock()]
            if state == PipelineState.TESTING:
                return [MagicMock()]
            return []

        mock_state_store.list_pipelines.side_effect = list_pipelines_side_effect

        result = scheduler.sync("project-1", mock_kanban, mock_git_manager)

        assert result.started == []
        assert result.remaining == 3
        mock_orchestrator.start_pipeline.assert_not_called()
