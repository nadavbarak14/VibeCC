"""Unit tests for GitManager."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from vibecc.git_manager import (
    PR,
    BranchError,
    CIStatus,
    GitManager,
    MergeError,
    PRError,
    PushError,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock HTTP client."""
    return MagicMock()


@pytest.fixture
def manager(mock_client: MagicMock) -> GitManager:
    """Create a GitManager instance with mocked client."""
    mgr = GitManager(
        repo="owner/repo",
        token="test-token",
        repo_path="/tmp/test-repo",
    )
    mgr._client = mock_client
    return mgr


@pytest.mark.unit
class TestCreateBranch:
    """Tests for create_branch."""

    def test_create_branch_names_correctly(self, manager: GitManager) -> None:
        """Branch named `ticket-{id}`."""
        with patch.object(manager, "_run_git"):
            branch = manager.create_branch("42")

            assert branch == "ticket-42"

    def test_create_branch_from_base(self, manager: GitManager) -> None:
        """Creates from specified base."""
        with patch.object(manager, "_run_git") as mock_git:
            manager.create_branch("123", base="develop")

            # Verify fetch was called with correct base
            mock_git.assert_any_call("fetch", "origin", "develop")
            # Verify checkout was called with correct arguments
            mock_git.assert_any_call("checkout", "-b", "ticket-123", "origin/develop")

    def test_create_branch_default_base_is_main(self, manager: GitManager) -> None:
        """Default base branch is main."""
        with patch.object(manager, "_run_git") as mock_git:
            manager.create_branch("99")

            mock_git.assert_any_call("fetch", "origin", "main")
            mock_git.assert_any_call("checkout", "-b", "ticket-99", "origin/main")

    def test_create_branch_failure_raises_error(self, manager: GitManager) -> None:
        """BranchError raised on git failure."""
        with patch.object(manager, "_run_git") as mock_git:
            mock_git.side_effect = subprocess.CalledProcessError(
                1, "git", stderr="branch already exists"
            )

            with pytest.raises(BranchError) as exc_info:
                manager.create_branch("42")

            assert "ticket-42" in str(exc_info.value)


@pytest.mark.unit
class TestPush:
    """Tests for push."""

    def test_push_calls_git(self, manager: GitManager) -> None:
        """Push triggered with correct arguments."""
        with patch.object(manager, "_run_git") as mock_git:
            manager.push("ticket-42")

            mock_git.assert_called_once_with("push", "-u", "origin", "ticket-42")

    def test_push_failure_raises_error(self, manager: GitManager) -> None:
        """PushError raised on git failure."""
        with patch.object(manager, "_run_git") as mock_git:
            mock_git.side_effect = subprocess.CalledProcessError(1, "git", stderr="push rejected")

            with pytest.raises(PushError) as exc_info:
                manager.push("ticket-42")

            assert "ticket-42" in str(exc_info.value)


@pytest.mark.unit
class TestCreatePR:
    """Tests for create_pr."""

    def test_create_pr_returns_pr_object(self, manager: GitManager, mock_client: MagicMock) -> None:
        """PR with id, url, number returned."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 12345,
            "html_url": "https://github.com/owner/repo/pull/1",
            "number": 1,
        }
        mock_client.post.return_value = mock_response

        pr = manager.create_pr(
            branch="ticket-42",
            title="Add feature",
            body="This adds a new feature",
        )

        assert isinstance(pr, PR)
        assert pr.id == 12345
        assert pr.url == "https://github.com/owner/repo/pull/1"
        assert pr.number == 1

    def test_create_pr_sends_correct_payload(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """Correct data sent to GitHub API."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 1,
            "html_url": "https://github.com/owner/repo/pull/1",
            "number": 1,
        }
        mock_client.post.return_value = mock_response

        manager.create_pr(
            branch="ticket-42",
            title="My Title",
            body="My Body",
            base="develop",
        )

        mock_client.post.assert_called_once_with(
            "/repos/owner/repo/pulls",
            json={
                "title": "My Title",
                "body": "My Body",
                "head": "ticket-42",
                "base": "develop",
            },
        )

    def test_create_pr_failure_raises_error(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """PRError raised on API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Validation failed"
        mock_client.post.return_value = mock_response

        with pytest.raises(PRError) as exc_info:
            manager.create_pr("ticket-42", "Title", "Body")

        assert "422" in str(exc_info.value)


@pytest.mark.unit
class TestGetCIStatus:
    """Tests for get_pr_ci_status."""

    def _mock_pr_response(self, sha: str = "abc123") -> MagicMock:
        """Create a mock PR response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"head": {"sha": sha}}
        return response

    def _mock_status_response(self, state: str) -> MagicMock:
        """Create a mock status response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"state": state}
        return response

    def _mock_checks_response(self, check_runs: list) -> MagicMock:
        """Create a mock check runs response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"check_runs": check_runs}
        return response

    def test_get_ci_status_pending(self, manager: GitManager, mock_client: MagicMock) -> None:
        """Returns PENDING when checks running."""
        mock_client.get.side_effect = [
            self._mock_pr_response(),
            self._mock_status_response("pending"),
            self._mock_checks_response([{"status": "in_progress", "conclusion": None}]),
        ]

        status = manager.get_pr_ci_status(1)

        assert status == CIStatus.PENDING

    def test_get_ci_status_success(self, manager: GitManager, mock_client: MagicMock) -> None:
        """Returns SUCCESS when all pass."""
        mock_client.get.side_effect = [
            self._mock_pr_response(),
            self._mock_status_response("success"),
            self._mock_checks_response([{"status": "completed", "conclusion": "success"}]),
        ]

        status = manager.get_pr_ci_status(1)

        assert status == CIStatus.SUCCESS

    def test_get_ci_status_failure(self, manager: GitManager, mock_client: MagicMock) -> None:
        """Returns FAILURE when any fails."""
        mock_client.get.side_effect = [
            self._mock_pr_response(),
            self._mock_status_response("failure"),
            self._mock_checks_response([{"status": "completed", "conclusion": "failure"}]),
        ]

        status = manager.get_pr_ci_status(1)

        assert status == CIStatus.FAILURE

    def test_get_ci_status_with_mixed_checks(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """Returns FAILURE if any check fails even if others pass."""
        mock_client.get.side_effect = [
            self._mock_pr_response(),
            self._mock_status_response("failure"),
            self._mock_checks_response(
                [
                    {"status": "completed", "conclusion": "success"},
                    {"status": "completed", "conclusion": "failure"},
                ]
            ),
        ]

        status = manager.get_pr_ci_status(1)

        assert status == CIStatus.FAILURE


@pytest.mark.unit
class TestMergePR:
    """Tests for merge_pr."""

    def test_merge_pr_uses_rebase(self, manager: GitManager, mock_client: MagicMock) -> None:
        """Rebase strategy used."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.put.return_value = mock_response

        manager.merge_pr(1)

        mock_client.put.assert_called_once_with(
            "/repos/owner/repo/pulls/1/merge",
            json={"merge_method": "rebase"},
        )

    def test_merge_pr_failure_raises_error(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """MergeError raised on API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 405
        mock_response.text = "PR not mergeable"
        mock_client.put.return_value = mock_response

        with pytest.raises(MergeError) as exc_info:
            manager.merge_pr(1)

        assert "405" in str(exc_info.value)


@pytest.mark.unit
class TestDeleteBranch:
    """Tests for delete_branch."""

    def test_delete_branch_removes_remote(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """Branch deleted via API."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.delete.return_value = mock_response

        manager.delete_branch("ticket-42")

        mock_client.delete.assert_called_once_with("/repos/owner/repo/git/refs/heads/ticket-42")

    def test_delete_branch_already_deleted_succeeds(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """No error if branch already deleted (422)."""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_client.delete.return_value = mock_response

        # Should not raise
        manager.delete_branch("ticket-42")

    def test_delete_branch_failure_raises_error(
        self, manager: GitManager, mock_client: MagicMock
    ) -> None:
        """BranchError raised on API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_client.delete.return_value = mock_response

        with pytest.raises(BranchError) as exc_info:
            manager.delete_branch("ticket-42")

        assert "403" in str(exc_info.value)
