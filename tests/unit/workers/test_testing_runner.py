"""Unit tests for Testing Runner."""

from unittest.mock import MagicMock, patch

import pytest

from vibecc.git_manager import PR, CIStatus, GitManager
from vibecc.workers import TestingResult, TestingRunner, TestingTask


@pytest.fixture
def task() -> TestingTask:
    """Create a sample testing task."""
    return TestingTask(
        ticket_id="42",
        ticket_title="Add user authentication",
        branch="ticket-42",
        repo_path="/path/to/repo",
    )


@pytest.fixture
def mock_git_manager() -> MagicMock:
    """Create a mock GitManager."""
    manager = MagicMock(spec=GitManager)
    manager.repo = "owner/repo"
    return manager


@pytest.fixture
def runner(mock_git_manager: MagicMock) -> TestingRunner:
    """Create a TestingRunner with mocked GitManager."""
    return TestingRunner(git_manager=mock_git_manager, poll_interval=0)


@pytest.mark.unit
class TestExecute:
    """Tests for execute method."""

    def test_execute_pushes_branch(
        self, runner: TestingRunner, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """Push called with correct branch."""
        mock_git_manager.create_pr.return_value = PR(id=1, url="https://example.com/pr/1", number=1)
        mock_git_manager.get_pr_ci_status.return_value = CIStatus.SUCCESS

        runner.execute(task)

        mock_git_manager.push.assert_called_once_with(task.branch)

    def test_execute_creates_pr(
        self, runner: TestingRunner, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """PR created with correct title and body."""
        mock_git_manager.create_pr.return_value = PR(id=1, url="https://example.com/pr/1", number=1)
        mock_git_manager.get_pr_ci_status.return_value = CIStatus.SUCCESS

        runner.execute(task)

        mock_git_manager.create_pr.assert_called_once_with(
            branch="ticket-42",
            title="#42: Add user authentication",
            body="Closes #42",
        )

    def test_execute_polls_ci_status(
        self, runner: TestingRunner, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """CI status checked."""
        mock_git_manager.create_pr.return_value = PR(id=1, url="https://example.com/pr/1", number=1)
        mock_git_manager.get_pr_ci_status.return_value = CIStatus.SUCCESS

        runner.execute(task)

        mock_git_manager.get_pr_ci_status.assert_called_with(1)

    def test_execute_returns_success_on_ci_pass(
        self, runner: TestingRunner, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """Success result when CI passes."""
        mock_git_manager.create_pr.return_value = PR(
            id=12345, url="https://github.com/owner/repo/pull/1", number=1
        )
        mock_git_manager.get_pr_ci_status.return_value = CIStatus.SUCCESS

        result = runner.execute(task)

        assert result.success is True
        assert result.pr_id == 12345
        assert result.pr_url == "https://github.com/owner/repo/pull/1"
        assert result.ci_status == CIStatus.SUCCESS
        assert result.failure_logs is None

    def test_execute_returns_failure_on_ci_fail(
        self, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """Failure result with logs when CI fails."""
        runner = TestingRunner(git_manager=mock_git_manager, poll_interval=0)
        mock_git_manager.create_pr.return_value = PR(
            id=12345, url="https://github.com/owner/repo/pull/1", number=1
        )
        mock_git_manager.get_pr_ci_status.return_value = CIStatus.FAILURE

        # Mock the client for fetching failure logs
        mock_client = MagicMock()
        mock_git_manager.client = mock_client

        # Mock PR response
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {"head": {"sha": "abc123"}}

        # Mock check runs response with a failure
        mock_checks_response = MagicMock()
        mock_checks_response.status_code = 200
        mock_checks_response.json.return_value = {
            "check_runs": [
                {
                    "name": "test",
                    "conclusion": "failure",
                    "output": {
                        "title": "Tests failed",
                        "summary": "2 tests failed",
                    },
                }
            ]
        }

        mock_client.get.side_effect = [mock_pr_response, mock_checks_response]

        result = runner.execute(task)

        assert result.success is False
        assert result.ci_status == CIStatus.FAILURE
        assert result.failure_logs is not None
        assert "test" in result.failure_logs
        assert "failure" in result.failure_logs

    def test_execute_waits_while_pending(
        self, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """Keeps polling while CI is pending."""
        runner = TestingRunner(git_manager=mock_git_manager, poll_interval=0)
        mock_git_manager.create_pr.return_value = PR(id=1, url="https://example.com/pr/1", number=1)
        mock_git_manager.get_pr_ci_status.side_effect = [
            CIStatus.PENDING,
            CIStatus.PENDING,
            CIStatus.SUCCESS,
        ]

        result = runner.execute(task)

        assert result.success is True
        assert mock_git_manager.get_pr_ci_status.call_count == 3


@pytest.mark.unit
class TestPolling:
    """Tests for CI polling behavior."""

    def test_poll_interval_configurable(self, mock_git_manager: MagicMock) -> None:
        """Poll interval can be configured."""
        runner = TestingRunner(git_manager=mock_git_manager, poll_interval=60)
        assert runner.poll_interval == 60

    def test_default_poll_interval(self, mock_git_manager: MagicMock) -> None:
        """Default poll interval is 30 seconds."""
        runner = TestingRunner(git_manager=mock_git_manager)
        assert runner.poll_interval == 30

    def test_max_polls_limits_polling(self, mock_git_manager: MagicMock, task: TestingTask) -> None:
        """Max polls limits how many times CI is checked."""
        runner = TestingRunner(git_manager=mock_git_manager, poll_interval=0, max_polls=3)
        mock_git_manager.create_pr.return_value = PR(id=1, url="https://example.com/pr/1", number=1)
        mock_git_manager.get_pr_ci_status.return_value = CIStatus.PENDING

        # Mock for failure logs (needed because max polls reached = failure)
        mock_client = MagicMock()
        mock_git_manager.client = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"head": {"sha": "abc"}}
        mock_checks_response = MagicMock()
        mock_checks_response.status_code = 200
        mock_checks_response.json.return_value = {"check_runs": []}
        mock_client.get.side_effect = [mock_response, mock_checks_response]

        result = runner.execute(task)

        assert result.success is False
        assert result.ci_status == CIStatus.FAILURE
        assert mock_git_manager.get_pr_ci_status.call_count == 3

    @patch("vibecc.workers.testing.time.sleep")
    def test_sleeps_between_polls(
        self, mock_sleep: MagicMock, mock_git_manager: MagicMock, task: TestingTask
    ) -> None:
        """Sleep called between polls."""
        runner = TestingRunner(git_manager=mock_git_manager, poll_interval=30)
        mock_git_manager.create_pr.return_value = PR(id=1, url="https://example.com/pr/1", number=1)
        mock_git_manager.get_pr_ci_status.side_effect = [CIStatus.PENDING, CIStatus.SUCCESS]

        runner.execute(task)

        mock_sleep.assert_called_with(30)


@pytest.mark.unit
class TestFailureLogs:
    """Tests for failure log fetching."""

    def test_fetch_failure_logs_returns_check_info(
        self, runner: TestingRunner, mock_git_manager: MagicMock
    ) -> None:
        """Failure logs include check name and output."""
        mock_client = MagicMock()
        mock_git_manager.client = mock_client

        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {"head": {"sha": "abc123"}}

        mock_checks_response = MagicMock()
        mock_checks_response.status_code = 200
        mock_checks_response.json.return_value = {
            "check_runs": [
                {
                    "name": "pytest",
                    "conclusion": "failure",
                    "output": {
                        "title": "Test failures",
                        "summary": "test_auth.py::test_login FAILED",
                    },
                }
            ]
        }

        mock_client.get.side_effect = [mock_pr_response, mock_checks_response]

        logs = runner._fetch_failure_logs(1)

        assert "pytest" in logs
        assert "failure" in logs
        assert "test_auth.py::test_login FAILED" in logs

    def test_fetch_failure_logs_handles_multiple_failures(
        self, runner: TestingRunner, mock_git_manager: MagicMock
    ) -> None:
        """Multiple failed checks are included."""
        mock_client = MagicMock()
        mock_git_manager.client = mock_client

        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {"head": {"sha": "abc123"}}

        mock_checks_response = MagicMock()
        mock_checks_response.status_code = 200
        mock_checks_response.json.return_value = {
            "check_runs": [
                {"name": "lint", "conclusion": "failure", "output": {}},
                {"name": "test", "conclusion": "failure", "output": {}},
                {"name": "build", "conclusion": "success", "output": {}},
            ]
        }

        mock_client.get.side_effect = [mock_pr_response, mock_checks_response]

        logs = runner._fetch_failure_logs(1)

        assert "lint" in logs
        assert "test" in logs
        assert "build" not in logs  # Success should not be included

    def test_fetch_failure_logs_handles_api_error(
        self, runner: TestingRunner, mock_git_manager: MagicMock
    ) -> None:
        """Gracefully handles API errors."""
        mock_client = MagicMock()
        mock_git_manager.client = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.get.return_value = mock_response

        logs = runner._fetch_failure_logs(1)

        assert "Failed to fetch" in logs


@pytest.mark.unit
class TestResultDataclass:
    """Tests for TestingResult dataclass."""

    def test_testing_result_fields(self) -> None:
        """TestingResult has all required fields."""
        result = TestingResult(
            success=True,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/1",
            ci_status=CIStatus.SUCCESS,
            failure_logs=None,
        )

        assert result.success is True
        assert result.pr_id == 123
        assert result.pr_url == "https://github.com/owner/repo/pull/1"
        assert result.ci_status == CIStatus.SUCCESS
        assert result.failure_logs is None

    def test_testing_result_with_failure_logs(self) -> None:
        """TestingResult can include failure logs."""
        result = TestingResult(
            success=False,
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/1",
            ci_status=CIStatus.FAILURE,
            failure_logs="Test failed: assert 1 == 2",
        )

        assert result.success is False
        assert result.failure_logs == "Test failed: assert 1 == 2"


@pytest.mark.unit
class TestTaskDataclass:
    """Tests for TestingTask dataclass."""

    def test_testing_task_fields(self) -> None:
        """TestingTask has all required fields."""
        task = TestingTask(
            ticket_id="42",
            ticket_title="Add feature",
            branch="ticket-42",
            repo_path="/path/to/repo",
        )

        assert task.ticket_id == "42"
        assert task.ticket_title == "Add feature"
        assert task.branch == "ticket-42"
        assert task.repo_path == "/path/to/repo"
