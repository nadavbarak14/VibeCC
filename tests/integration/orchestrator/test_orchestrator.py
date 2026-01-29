"""Integration tests for Orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vibecc.api.events import EventManager
from vibecc.git_manager import CIStatus
from vibecc.kanban import Ticket
from vibecc.orchestrator import Orchestrator
from vibecc.state_store import PipelineState, StateStore
from vibecc.workers import CodingResult, TestingResult


@pytest.fixture
def temp_db() -> str:
    """Create a temporary database file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test.db")


@pytest.fixture
def state_store(temp_db: str) -> StateStore:
    """Create a real StateStore with temp database."""
    store = StateStore(db_path=temp_db)
    yield store
    store.close()


@pytest.fixture
def event_manager() -> EventManager:
    """Create a real EventManager."""
    return EventManager()


@pytest.fixture
def orchestrator(state_store: StateStore, event_manager: EventManager) -> Orchestrator:
    """Create an Orchestrator with real StateStore."""
    return Orchestrator(
        state_store=state_store,
        event_manager=event_manager,
    )


@pytest.fixture
def project(state_store: StateStore) -> MagicMock:
    """Create a real project in the database."""
    return state_store.create_project(
        name="Test Project",
        repo="owner/repo",
        base_branch="main",
        max_retries_ci=3,
        max_retries_review=3,
    )


@pytest.fixture
def mock_git_manager() -> MagicMock:
    """Create a mock GitManager."""
    manager = MagicMock()
    manager.create_branch.return_value = "ticket-42"
    manager.repo_path = "/tmp/test-repo"  # Real path for subprocess calls
    return manager


@pytest.fixture(autouse=True)
def mock_subprocess():
    """Mock subprocess for branch checkout operations."""
    with patch("vibecc.orchestrator.orchestrator.subprocess") as mock:
        mock.run.return_value.returncode = 0
        yield mock


@pytest.fixture
def mock_kanban() -> MagicMock:
    """Create a mock KanbanAdapter."""
    return MagicMock()


@pytest.fixture
def mock_coder_worker() -> MagicMock:
    """Create a mock CoderWorker."""
    worker = MagicMock()
    worker.execute.return_value = CodingResult(
        success=True,
        output="Task completed",
        error=None,
    )
    return worker


@pytest.fixture
def mock_testing_runner() -> MagicMock:
    """Create a mock TestingRunner."""
    runner = MagicMock()
    runner.execute.return_value = TestingResult(
        success=True,
        pr_id=123,
        pr_url="https://github.com/owner/repo/pull/123",
        ci_status=CIStatus.SUCCESS,
        failure_logs=None,
    )
    return runner


@pytest.fixture
def sample_ticket() -> Ticket:
    """Create a sample ticket."""
    return Ticket(
        id="42",
        title="Add feature",
        body="Implement new feature",
        labels=[],
    )


@pytest.mark.integration
class TestFullPipelineHappyPath:
    """Tests for full pipeline happy path."""

    def test_full_pipeline_happy_path(
        self,
        orchestrator: Orchestrator,
        state_store: StateStore,
        project: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_ticket: Ticket,
    ) -> None:
        """Queue -> Code -> Test -> Merged."""
        # Start pipeline
        pipeline = orchestrator.start_pipeline(
            project_id=project.id,
            ticket=sample_ticket,
            git_manager=mock_git_manager,
        )

        # Verify initial state
        assert pipeline.state == PipelineState.QUEUED.value

        # Process QUEUED -> CODING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.CODING.value

        # Process CODING -> TESTING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.TESTING.value

        # Process TESTING -> MERGED
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.MERGED.value

        # Verify PR was merged
        mock_git_manager.merge_pr.assert_called_once_with(123)

        # Verify branch was deleted
        mock_git_manager.delete_branch.assert_called_once_with("ticket-42")

        # Verify ticket was closed
        mock_kanban.close_ticket.assert_called_once_with("42")

        # Verify history was saved
        history = state_store.get_history(project_id=project.id)
        assert len(history) == 1
        assert history[0].final_state == PipelineState.MERGED.value


@pytest.mark.integration
class TestPipelineWithCIRetry:
    """Tests for pipeline with CI retry."""

    def test_pipeline_with_ci_retry(
        self,
        orchestrator: Orchestrator,
        state_store: StateStore,
        project: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_ticket: Ticket,
    ) -> None:
        """CI fails, retries, then passes."""
        # Start pipeline
        pipeline = orchestrator.start_pipeline(
            project_id=project.id,
            ticket=sample_ticket,
            git_manager=mock_git_manager,
        )

        # Process QUEUED -> CODING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Process CODING -> TESTING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.TESTING.value

        # First CI fails
        mock_testing_runner.execute.return_value = TestingResult(
            success=False,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            ci_status=CIStatus.FAILURE,
            failure_logs="Test failed: test_foo",
        )

        # Process TESTING -> CODING (retry)
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.CODING.value
        assert pipeline.retry_count_ci == 1
        assert pipeline.feedback == "Test failed: test_foo"

        # Coder fixes the issue and succeeds
        mock_coder_worker.execute.return_value = CodingResult(
            success=True,
            output="Fixed the issue",
            error=None,
        )

        # Process CODING -> TESTING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.TESTING.value

        # CI passes this time
        mock_testing_runner.execute.return_value = TestingResult(
            success=True,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            ci_status=CIStatus.SUCCESS,
            failure_logs=None,
        )

        # Process TESTING -> MERGED
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.MERGED.value

        # Verify history
        history = state_store.get_history(project_id=project.id)
        assert len(history) == 1
        assert history[0].final_state == PipelineState.MERGED.value
        assert history[0].total_retries_ci == 1


@pytest.mark.integration
class TestPipelineMaxRetries:
    """Tests for pipeline max retries."""

    def test_pipeline_max_retries_fails(
        self,
        orchestrator: Orchestrator,
        state_store: StateStore,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_ticket: Ticket,
    ) -> None:
        """Pipeline fails after max retries exceeded."""
        # Create project with max_retries_ci = 2
        project = state_store.create_project(
            name="Test Project 2",
            repo="owner/repo2",
            base_branch="main",
            max_retries_ci=2,
        )

        # Start pipeline
        pipeline = orchestrator.start_pipeline(
            project_id=project.id,
            ticket=sample_ticket,
            git_manager=mock_git_manager,
        )

        # Start autopilot
        orchestrator.start_autopilot(project.id)

        # Process QUEUED -> CODING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Process CODING -> TESTING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # CI fails - retry 1
        mock_testing_runner.execute.return_value = TestingResult(
            success=False,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            ci_status=CIStatus.FAILURE,
            failure_logs="Test failed",
        )

        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.CODING.value
        assert pipeline.retry_count_ci == 1

        # Process CODING -> TESTING
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # CI fails again - retry 2 (max reached)
        orchestrator.process_pipeline(
            pipeline_id=pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        pipeline = state_store.get_pipeline(pipeline.id)
        assert pipeline.state == PipelineState.FAILED.value
        assert pipeline.retry_count_ci == 2

        # Verify autopilot stopped
        status = orchestrator.get_autopilot_status(project.id)
        assert status.running is False

        # Verify history
        history = state_store.get_history(project_id=project.id)
        assert len(history) == 1
        assert history[0].final_state == PipelineState.FAILED.value
