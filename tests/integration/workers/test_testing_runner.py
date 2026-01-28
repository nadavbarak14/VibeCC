"""Integration tests for Testing Runner.

These tests require:
- GITHUB_TOKEN environment variable
- GITHUB_TEST_REPO environment variable (e.g., "owner/test-repo")
- A cloned test repository

Run with: pytest tests/integration/workers/test_testing_runner.py -m real
"""

import contextlib
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

import pytest

from vibecc.git_manager import CIStatus, GitManager
from vibecc.workers import TestingRunner, TestingTask

# Skip all tests in this module if credentials not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.real,
    pytest.mark.skipif(
        not os.environ.get("GITHUB_TOKEN") or not os.environ.get("GITHUB_TEST_REPO"),
        reason="GITHUB_TOKEN and GITHUB_TEST_REPO required",
    ),
]


@pytest.fixture
def github_token() -> str:
    """Get GitHub token from environment."""
    return os.environ["GITHUB_TOKEN"]


@pytest.fixture
def test_repo() -> str:
    """Get test repo from environment."""
    return os.environ["GITHUB_TEST_REPO"]


@pytest.fixture
def temp_clone(test_repo: str, github_token: str):
    """Clone test repo to a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "repo"
        # Clone with token for push access
        clone_url = f"https://x-access-token:{github_token}@github.com/{test_repo}.git"
        subprocess.run(
            ["git", "clone", clone_url, str(repo_path)],
            check=True,
            capture_output=True,
        )
        # Configure git user for commits
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
        )
        yield repo_path


@pytest.fixture
def git_manager(test_repo: str, github_token: str, temp_clone: Path) -> GitManager:
    """Create a GitManager for the test repo."""
    mgr = GitManager(
        repo=test_repo,
        token=github_token,
        repo_path=temp_clone,
    )
    yield mgr
    mgr.close()


class TestFullPRCICycle:
    """Integration test for complete PR/CI lifecycle using Testing Runner."""

    def test_full_pr_ci_cycle(self, git_manager: GitManager, temp_clone: Path) -> None:
        """Push → PR → CI passes → success result."""
        # Use unique ID to avoid conflicts
        ticket_id = f"test-{uuid.uuid4().hex[:8]}"
        branch_name = f"ticket-{ticket_id}"

        try:
            # 1. Create branch and make a commit (simulating what Coder Worker does)
            git_manager.create_branch(ticket_id)

            test_file = temp_clone / f"test-{ticket_id}.txt"
            test_file.write_text(f"Test content for {ticket_id}")
            subprocess.run(
                ["git", "add", str(test_file)],
                cwd=temp_clone,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Test commit for {ticket_id}"],
                cwd=temp_clone,
                check=True,
            )

            # 2. Create Testing Runner and execute
            runner = TestingRunner(
                git_manager=git_manager,
                poll_interval=5,  # Faster polling for tests
                max_polls=12,  # Max 60 seconds
            )

            task = TestingTask(
                ticket_id=ticket_id,
                ticket_title=f"Test PR {ticket_id}",
                branch=branch_name,
                repo_path=str(temp_clone),
            )

            result = runner.execute(task)

            # 3. Verify result
            assert result.pr_id > 0
            assert result.pr_url.startswith("https://github.com/")
            assert result.ci_status in [CIStatus.SUCCESS, CIStatus.FAILURE, CIStatus.PENDING]

            # If CI passed or no CI configured (pending after timeout), we're good
            if result.ci_status == CIStatus.SUCCESS:
                assert result.success is True
                assert result.failure_logs is None
            elif result.ci_status == CIStatus.FAILURE:
                assert result.success is False
                # Failure logs should be populated
                assert result.failure_logs is not None

            # 4. Cleanup - delete branch
            git_manager.delete_branch(branch_name)

        except Exception:
            # Cleanup on failure - try to delete branch if it exists
            with contextlib.suppress(Exception):
                git_manager.delete_branch(branch_name)
            raise
