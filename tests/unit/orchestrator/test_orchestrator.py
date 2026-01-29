"""Unit tests for Orchestrator."""

from unittest.mock import MagicMock, patch

import pytest

from vibecc.api.events import EventManager
from vibecc.git_manager import CIStatus
from vibecc.kanban import Ticket
from vibecc.orchestrator import Orchestrator
from vibecc.state_store import PipelineState
from vibecc.workers import CodingResult, TestingResult


@pytest.fixture
def mock_state_store() -> MagicMock:
    """Create a mock StateStore."""
    store = MagicMock()
    return store


@pytest.fixture
def mock_event_manager() -> MagicMock:
    """Create a mock EventManager."""
    manager = MagicMock(spec=EventManager)
    return manager


@pytest.fixture
def mock_git_manager() -> MagicMock:
    """Create a mock GitManager."""
    manager = MagicMock()
    manager.create_branch.return_value = "ticket-42"
    manager.repo_path = "/tmp/test-repo"  # Real path for subprocess calls
    return manager


@pytest.fixture
def mock_kanban() -> MagicMock:
    """Create a mock KanbanAdapter."""
    kanban = MagicMock()
    return kanban


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
def orchestrator(mock_state_store: MagicMock, mock_event_manager: MagicMock) -> Orchestrator:
    """Create an Orchestrator instance with mocked dependencies."""
    return Orchestrator(
        state_store=mock_state_store,
        event_manager=mock_event_manager,
    )


@pytest.fixture
def sample_project() -> MagicMock:
    """Create a sample project."""
    project = MagicMock()
    project.id = "project-123"
    project.name = "Test Project"
    project.repo = "owner/repo"
    project.base_branch = "main"
    project.max_retries_ci = 3
    project.max_retries_review = 3
    return project


@pytest.fixture
def sample_pipeline() -> MagicMock:
    """Create a sample pipeline."""
    pipeline = MagicMock()
    pipeline.id = "pipeline-456"
    pipeline.project_id = "project-123"
    pipeline.ticket_id = "42"
    pipeline.ticket_title = "Add feature"
    pipeline.ticket_body = "Implement new feature"
    pipeline.state = PipelineState.QUEUED.value
    pipeline.pipeline_state = PipelineState.QUEUED
    pipeline.branch_name = "ticket-42"
    pipeline.pr_id = None
    pipeline.pr_url = None
    pipeline.retry_count_ci = 0
    pipeline.retry_count_review = 0
    pipeline.feedback = None
    return pipeline


@pytest.fixture
def sample_ticket() -> Ticket:
    """Create a sample ticket."""
    return Ticket(
        id="42",
        title="Add feature",
        body="Implement new feature",
        labels=[],
    )


@pytest.mark.unit
class TestStartPipeline:
    """Tests for start_pipeline method."""

    def test_start_pipeline_creates_record(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
        sample_ticket: Ticket,
    ) -> None:
        """Pipeline created in state store."""
        mock_state_store.get_project.return_value = sample_project
        mock_state_store.create_pipeline.return_value = sample_pipeline

        pipeline = orchestrator.start_pipeline(
            project_id=sample_project.id,
            ticket=sample_ticket,
            git_manager=mock_git_manager,
        )

        # Verify branch created
        mock_git_manager.create_branch.assert_called_once_with(
            sample_ticket.id, sample_project.base_branch
        )

        # Verify pipeline created
        mock_state_store.create_pipeline.assert_called_once_with(
            project_id=sample_project.id,
            ticket_id=sample_ticket.id,
            ticket_title=sample_ticket.title,
            branch_name="ticket-42",
            ticket_body=sample_ticket.body,
        )

        # Verify event emitted
        mock_event_manager.emit_pipeline_created.assert_called_once()

        assert pipeline == sample_pipeline


@pytest.mark.unit
class TestProcessQueuedState:
    """Tests for processing QUEUED state."""

    def test_queued_moves_to_coding(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """QUEUED state creates branch and moves to CODING."""
        sample_pipeline.state = PipelineState.QUEUED.value
        sample_pipeline.pipeline_state = PipelineState.QUEUED

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify state updated to CODING
        mock_state_store.update_pipeline.assert_called_with(
            sample_pipeline.id,
            state=PipelineState.CODING,
        )

        # Verify event emitted
        mock_event_manager.emit_pipeline_updated.assert_called()
        call_kwargs = mock_event_manager.emit_pipeline_updated.call_args[1]
        assert call_kwargs["state"] == PipelineState.CODING.value


@pytest.mark.unit
class TestProcessCodingState:
    """Tests for processing CODING state."""

    @patch("vibecc.orchestrator.orchestrator.subprocess")
    def test_coding_success_moves_to_testing(
        self,
        mock_subprocess: MagicMock,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """Coder success transitions to TESTING."""
        # Mock subprocess for branch checkout
        mock_subprocess.run.return_value.returncode = 0

        sample_pipeline.state = PipelineState.CODING.value
        sample_pipeline.pipeline_state = PipelineState.CODING

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        # Coder succeeds
        mock_coder_worker.execute.return_value = CodingResult(
            success=True,
            output="Task completed",
            error=None,
        )

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify coder was called
        mock_coder_worker.execute.assert_called_once()

        # Verify state updated to TESTING
        mock_state_store.update_pipeline.assert_called_with(
            sample_pipeline.id,
            state=PipelineState.TESTING,
            feedback=None,
        )

        # Verify event emitted
        mock_event_manager.emit_pipeline_updated.assert_called()
        call_kwargs = mock_event_manager.emit_pipeline_updated.call_args[1]
        assert call_kwargs["state"] == PipelineState.TESTING.value

    @patch("vibecc.orchestrator.orchestrator.subprocess")
    def test_coding_failure_moves_to_failed(
        self,
        mock_subprocess: MagicMock,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """Coding failure moves to FAILED state."""
        # Mock subprocess for branch checkout
        mock_subprocess.run.return_value.returncode = 0

        sample_pipeline.state = PipelineState.CODING.value
        sample_pipeline.pipeline_state = PipelineState.CODING

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        # Coder fails
        mock_coder_worker.execute.return_value = CodingResult(
            success=False,
            output="",
            error="Coding failed",
        )

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify state updated to FAILED
        mock_state_store.update_pipeline.assert_called_with(
            sample_pipeline.id,
            state=PipelineState.FAILED,
            feedback="Coding failed",
        )

        # Verify pipeline completed event
        mock_event_manager.emit_pipeline_completed.assert_called_once()
        call_kwargs = mock_event_manager.emit_pipeline_completed.call_args[1]
        assert call_kwargs["final_state"] == PipelineState.FAILED.value

        # Verify autopilot stopped
        mock_event_manager.emit_autopilot_stopped.assert_called_once()


@pytest.mark.unit
class TestProcessTestingState:
    """Tests for processing TESTING state."""

    def test_testing_success_merges(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """Testing success merges PR and completes pipeline."""
        sample_pipeline.state = PipelineState.TESTING.value
        sample_pipeline.pipeline_state = PipelineState.TESTING

        # Return updated pipeline with PR info after update
        pipeline_with_pr = MagicMock()
        pipeline_with_pr.id = sample_pipeline.id
        pipeline_with_pr.project_id = sample_pipeline.project_id
        pipeline_with_pr.ticket_id = sample_pipeline.ticket_id
        pipeline_with_pr.branch_name = sample_pipeline.branch_name
        pipeline_with_pr.state = PipelineState.TESTING.value
        pipeline_with_pr.pr_id = 123
        pipeline_with_pr.pr_url = "https://github.com/owner/repo/pull/123"

        mock_state_store.get_pipeline.side_effect = [
            sample_pipeline,
            pipeline_with_pr,
            pipeline_with_pr,
        ]
        mock_state_store.get_project.return_value = sample_project

        # Testing succeeds
        mock_testing_runner.execute.return_value = TestingResult(
            success=True,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            ci_status=CIStatus.SUCCESS,
            failure_logs=None,
        )

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify PR merged
        mock_git_manager.merge_pr.assert_called_once_with(123)

        # Verify branch deleted
        mock_git_manager.delete_branch.assert_called_once_with(sample_pipeline.branch_name)

        # Verify ticket closed
        mock_kanban.close_ticket.assert_called_once_with(sample_pipeline.ticket_id)

        # Verify state updated to MERGED
        calls = mock_state_store.update_pipeline.call_args_list
        final_call = calls[-1]
        assert final_call[1]["state"] == PipelineState.MERGED

        # Verify pipeline completed event
        mock_event_manager.emit_pipeline_completed.assert_called_once()
        call_kwargs = mock_event_manager.emit_pipeline_completed.call_args[1]
        assert call_kwargs["final_state"] == PipelineState.MERGED.value

        # Verify saved to history
        mock_state_store.save_to_history.assert_called_once()

    def test_testing_failure_back_to_coding(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """CI failure goes back to CODING with feedback."""
        sample_pipeline.state = PipelineState.TESTING.value
        sample_pipeline.pipeline_state = PipelineState.TESTING
        sample_pipeline.retry_count_ci = 0

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        # Testing fails
        mock_testing_runner.execute.return_value = TestingResult(
            success=False,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            ci_status=CIStatus.FAILURE,
            failure_logs="Test failed: test_foo",
        )

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify state updated to CODING with feedback
        calls = mock_state_store.update_pipeline.call_args_list
        # Find the call that sets state to CODING
        coding_call = None
        for call in calls:
            if call[1].get("state") == PipelineState.CODING:
                coding_call = call
                break

        assert coding_call is not None
        assert coding_call[1]["retry_count_ci"] == 1
        assert coding_call[1]["feedback"] == "Test failed: test_foo"

        # Verify pipeline NOT completed (still retrying)
        mock_event_manager.emit_pipeline_completed.assert_not_called()


@pytest.mark.unit
class TestMaxRetries:
    """Tests for max retry handling."""

    def test_max_retries_moves_to_failed(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """Exceeding max retries moves to FAILED."""
        sample_pipeline.state = PipelineState.TESTING.value
        sample_pipeline.pipeline_state = PipelineState.TESTING
        sample_pipeline.retry_count_ci = 2  # Already at max - 1

        sample_project.max_retries_ci = 3

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        # Testing fails again
        mock_testing_runner.execute.return_value = TestingResult(
            success=False,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            ci_status=CIStatus.FAILURE,
            failure_logs="Test failed again",
        )

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify state updated to FAILED
        calls = mock_state_store.update_pipeline.call_args_list
        failed_call = None
        for call in calls:
            if call[1].get("state") == PipelineState.FAILED:
                failed_call = call
                break

        assert failed_call is not None
        assert failed_call[1]["retry_count_ci"] == 3

        # Verify pipeline completed
        mock_event_manager.emit_pipeline_completed.assert_called_once()
        call_kwargs = mock_event_manager.emit_pipeline_completed.call_args[1]
        assert call_kwargs["final_state"] == PipelineState.FAILED.value

        # Verify autopilot stopped
        mock_event_manager.emit_autopilot_stopped.assert_called_once()


@pytest.mark.unit
class TestAutopilot:
    """Tests for autopilot management."""

    @patch("vibecc.orchestrator.orchestrator.subprocess")
    def test_failed_stops_autopilot(
        self,
        mock_subprocess: MagicMock,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """Pipeline failure stops autopilot for project."""
        # Mock subprocess for branch checkout
        mock_subprocess.run.return_value.returncode = 0

        sample_pipeline.state = PipelineState.CODING.value
        sample_pipeline.pipeline_state = PipelineState.CODING

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        # Coder fails
        mock_coder_worker.execute.return_value = CodingResult(
            success=False,
            output="",
            error="Failed",
        )

        # Start autopilot first
        orchestrator.start_autopilot(sample_project.id)

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify autopilot stopped
        mock_event_manager.emit_autopilot_stopped.assert_called()

        # Verify autopilot status is false
        status = orchestrator.get_autopilot_status(sample_project.id)
        assert status.running is False


@pytest.mark.unit
class TestEventEmission:
    """Tests for event emission."""

    def test_emits_events_on_state_change(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """Events emitted for dashboard on state changes."""
        sample_pipeline.state = PipelineState.QUEUED.value
        sample_pipeline.pipeline_state = PipelineState.QUEUED

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify pipeline_updated event emitted
        mock_event_manager.emit_pipeline_updated.assert_called_once()

        # Verify log events emitted
        mock_event_manager.emit_log.assert_called()


@pytest.mark.unit
class TestLogging:
    """Tests for logging functionality."""

    @patch("vibecc.orchestrator.orchestrator.subprocess")
    def test_logs_all_steps(
        self,
        mock_subprocess: MagicMock,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        mock_git_manager: MagicMock,
        mock_kanban: MagicMock,
        mock_coder_worker: MagicMock,
        mock_testing_runner: MagicMock,
        sample_project: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """All actions logged for observability."""
        # Mock subprocess for branch checkout
        mock_subprocess.run.return_value.returncode = 0

        sample_pipeline.state = PipelineState.CODING.value
        sample_pipeline.pipeline_state = PipelineState.CODING

        mock_state_store.get_pipeline.return_value = sample_pipeline
        mock_state_store.get_project.return_value = sample_project

        mock_coder_worker.execute.return_value = CodingResult(
            success=True,
            output="Done",
            error=None,
        )

        orchestrator.process_pipeline(
            pipeline_id=sample_pipeline.id,
            git_manager=mock_git_manager,
            kanban=mock_kanban,
            coder_worker=mock_coder_worker,
            testing_runner=mock_testing_runner,
            repo_path="/path/to/repo",
        )

        # Verify multiple log events emitted
        assert mock_event_manager.emit_log.call_count >= 2


@pytest.mark.unit
class TestGetStatus:
    """Tests for get_status method."""

    def test_get_status_returns_pipeline(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        sample_pipeline: MagicMock,
    ) -> None:
        """get_status returns pipeline from state store."""
        mock_state_store.get_pipeline.return_value = sample_pipeline

        result = orchestrator.get_status(sample_pipeline.id)

        assert result == sample_pipeline
        mock_state_store.get_pipeline.assert_called_once_with(sample_pipeline.id)


@pytest.mark.unit
class TestAutopilotStatus:
    """Tests for autopilot status."""

    def test_get_autopilot_status(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        sample_project: MagicMock,
    ) -> None:
        """get_autopilot_status returns correct status."""
        mock_state_store.get_project.return_value = sample_project
        mock_state_store.list_pipelines.return_value = []

        status = orchestrator.get_autopilot_status(sample_project.id)

        assert status.project_id == sample_project.id
        assert status.running is False
        assert status.active_pipelines == 0

    def test_start_autopilot(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        sample_project: MagicMock,
    ) -> None:
        """start_autopilot sets running to True."""
        mock_state_store.get_project.return_value = sample_project
        mock_state_store.list_pipelines.return_value = []

        orchestrator.start_autopilot(sample_project.id)

        status = orchestrator.get_autopilot_status(sample_project.id)
        assert status.running is True

        mock_event_manager.emit_autopilot_started.assert_called_once_with(sample_project.id)

    def test_stop_autopilot(
        self,
        orchestrator: Orchestrator,
        mock_state_store: MagicMock,
        mock_event_manager: MagicMock,
        sample_project: MagicMock,
    ) -> None:
        """stop_autopilot sets running to False."""
        mock_state_store.get_project.return_value = sample_project
        mock_state_store.list_pipelines.return_value = []

        orchestrator.start_autopilot(sample_project.id)
        orchestrator.stop_autopilot(sample_project.id)

        status = orchestrator.get_autopilot_status(sample_project.id)
        assert status.running is False

        mock_event_manager.emit_autopilot_stopped.assert_called_once()
