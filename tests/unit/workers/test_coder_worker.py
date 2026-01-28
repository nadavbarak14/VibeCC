"""Unit tests for Coder Worker."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from vibecc.workers import CoderWorker, CodingTask


@pytest.fixture
def task() -> CodingTask:
    """Create a sample coding task."""
    return CodingTask(
        ticket_id="42",
        ticket_title="Add user authentication",
        ticket_body="Implement login/logout functionality with JWT tokens.",
        repo_path="/path/to/repo",
        branch="ticket-42",
        feedback=None,
    )


@pytest.fixture
def task_with_feedback() -> CodingTask:
    """Create a coding task with CI feedback."""
    return CodingTask(
        ticket_id="42",
        ticket_title="Add user authentication",
        ticket_body="Implement login/logout functionality with JWT tokens.",
        repo_path="/path/to/repo",
        branch="ticket-42",
        feedback="Test failed: test_login_success - AssertionError",
    )


@pytest.fixture
def worker() -> CoderWorker:
    """Create a CoderWorker instance."""
    return CoderWorker()


@pytest.mark.unit
class TestBuildPrompt:
    """Tests for prompt building."""

    def test_execute_builds_prompt(self, worker: CoderWorker, task: CodingTask) -> None:
        """Prompt includes ticket info."""
        prompt = worker.build_prompt(task)

        assert f"#{task.ticket_id}" in prompt
        assert task.ticket_title in prompt
        assert task.ticket_body in prompt
        assert "Complete this ticket" in prompt

    def test_execute_includes_feedback(
        self, worker: CoderWorker, task_with_feedback: CodingTask
    ) -> None:
        """Feedback included when present."""
        prompt = worker.build_prompt(task_with_feedback)

        assert task_with_feedback.feedback in prompt
        assert "Previous CI Feedback" in prompt

    def test_prompt_no_feedback_section_when_none(
        self, worker: CoderWorker, task: CodingTask
    ) -> None:
        """No feedback section when feedback is None."""
        prompt = worker.build_prompt(task)

        assert "Previous CI Feedback" not in prompt


@pytest.mark.unit
class TestExecute:
    """Tests for execute method."""

    def test_execute_calls_claude_cli(self, worker: CoderWorker, task: CodingTask) -> None:
        """Subprocess called correctly."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Task completed successfully"
        mock_result.stderr = ""

        with patch("vibecc.workers.coder.subprocess.run", return_value=mock_result) as mock_run:
            worker.execute(task)

            mock_run.assert_called_once()
            call_args = mock_run.call_args

            # Check command
            assert call_args[0][0] == ["claude", "-p", worker.build_prompt(task), "--yes"]

            # Check kwargs
            assert call_args[1]["cwd"] == task.repo_path
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["text"] is True

    def test_execute_success_returns_result(self, worker: CoderWorker, task: CodingTask) -> None:
        """Success result on exit 0."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully modified files"
        mock_result.stderr = ""

        with patch("vibecc.workers.coder.subprocess.run", return_value=mock_result):
            result = worker.execute(task)

            assert result.success is True
            assert "Successfully modified files" in result.output
            assert result.error is None

    def test_execute_failure_returns_error(self, worker: CoderWorker, task: CodingTask) -> None:
        """Failure result on non-zero exit."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Some output"
        mock_result.stderr = "Error occurred"

        with patch("vibecc.workers.coder.subprocess.run", return_value=mock_result):
            result = worker.execute(task)

            assert result.success is False
            assert "Some output" in result.output
            assert "Error occurred" in result.output
            assert result.error is not None
            assert "exited with code 1" in result.error

    def test_execute_captures_output(self, worker: CoderWorker, task: CodingTask) -> None:
        """Output captured for logging."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "stdout content"
        mock_result.stderr = "stderr content"

        with patch("vibecc.workers.coder.subprocess.run", return_value=mock_result):
            result = worker.execute(task)

            assert "stdout content" in result.output
            assert "stderr content" in result.output


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling."""

    def test_execute_handles_timeout(self, task: CodingTask) -> None:
        """Timeout returns error result."""
        worker = CoderWorker(timeout=30)

        with patch(
            "vibecc.workers.coder.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=30),
        ):
            result = worker.execute(task)

            assert result.success is False
            assert "timed out" in result.error.lower()

    def test_execute_handles_cli_not_found(self, worker: CoderWorker, task: CodingTask) -> None:
        """FileNotFoundError when CLI not installed."""
        with patch(
            "vibecc.workers.coder.subprocess.run",
            side_effect=FileNotFoundError("claude not found"),
        ):
            result = worker.execute(task)

            assert result.success is False
            assert "not found" in result.error.lower()
            assert "claude" in result.error.lower()

    def test_execute_handles_os_error(self, worker: CoderWorker, task: CodingTask) -> None:
        """OSError returns error result."""
        with patch(
            "vibecc.workers.coder.subprocess.run",
            side_effect=OSError("Permission denied"),
        ):
            result = worker.execute(task)

            assert result.success is False
            assert "Permission denied" in result.error


@pytest.mark.unit
class TestTimeout:
    """Tests for timeout configuration."""

    def test_default_timeout_is_none(self) -> None:
        """Default timeout is None (no timeout)."""
        worker = CoderWorker()
        assert worker.timeout is None

    def test_custom_timeout(self) -> None:
        """Custom timeout is set correctly."""
        worker = CoderWorker(timeout=60)
        assert worker.timeout == 60

    def test_timeout_passed_to_subprocess(self, task: CodingTask) -> None:
        """Timeout passed to subprocess.run."""
        worker = CoderWorker(timeout=120)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("vibecc.workers.coder.subprocess.run", return_value=mock_result) as mock_run:
            worker.execute(task)

            assert mock_run.call_args[1]["timeout"] == 120
