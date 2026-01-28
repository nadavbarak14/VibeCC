"""Integration tests for GitManager.

These tests require:
- GITHUB_TOKEN environment variable
- GITHUB_TEST_REPO environment variable (e.g., "owner/test-repo")
- A cloned test repository

Run with: pytest tests/integration/git_manager/ -m real
"""

import contextlib
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import pytest

from vibecc.git_manager import CIStatus, GitManager

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
def manager(test_repo: str, github_token: str, temp_clone: Path) -> GitManager:
    """Create a GitManager for the test repo."""
    mgr = GitManager(
        repo=test_repo,
        token=github_token,
        repo_path=temp_clone,
    )
    yield mgr
    mgr.close()


class TestFullBranchPRCycle:
    """Integration test for complete branch/PR lifecycle."""

    def test_full_branch_pr_cycle(self, manager: GitManager, temp_clone: Path) -> None:
        """Create branch -> push -> PR -> merge -> delete."""
        # Use unique ID to avoid conflicts
        ticket_id = f"test-{uuid.uuid4().hex[:8]}"

        try:
            # 1. Create branch
            branch = manager.create_branch(ticket_id)
            assert branch == f"ticket-{ticket_id}"

            # 2. Make a change and commit
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

            # 3. Push branch
            manager.push(branch)

            # 4. Create PR
            pr = manager.create_pr(
                branch=branch,
                title=f"Test PR for {ticket_id}",
                body="This is an automated test PR",
            )
            assert pr.number > 0
            assert pr.url.startswith("https://github.com/")

            # 5. Check CI status (might be pending immediately)
            status = manager.get_pr_ci_status(pr.number)
            assert status in [CIStatus.PENDING, CIStatus.SUCCESS, CIStatus.FAILURE]

            # 6. Wait for CI if pending (with timeout)
            max_wait = 60  # seconds
            waited = 0
            while status == CIStatus.PENDING and waited < max_wait:
                time.sleep(5)
                waited += 5
                status = manager.get_pr_ci_status(pr.number)

            # 7. Merge PR (only if CI passed or no CI configured)
            if status in [CIStatus.SUCCESS, CIStatus.PENDING]:
                manager.merge_pr(pr.number)

            # 8. Delete branch
            manager.delete_branch(branch)

        except Exception:
            # Cleanup on failure - try to delete branch if it exists
            with contextlib.suppress(Exception):
                manager.delete_branch(f"ticket-{ticket_id}")
            raise
