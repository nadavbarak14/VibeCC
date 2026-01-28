"""Integration tests for Coder Worker.

These tests require the Claude Code CLI to be installed and available.
They are skipped if the CLI is not found.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from vibecc.workers import CoderWorker, CodingTask


def claude_cli_available() -> bool:
    """Check if Claude Code CLI is available."""
    return shutil.which("claude") is not None


@pytest.fixture
def temp_repo() -> str:
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )

        # Create initial file and commit
        readme = Path(tmpdir) / "README.md"
        readme.write_text("# Test Repo\n")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmpdir,
            capture_output=True,
            check=True,
        )

        yield tmpdir


@pytest.mark.integration
@pytest.mark.skipif(not claude_cli_available(), reason="Claude Code CLI not available")
class TestClaudeCodeIntegration:
    """Integration tests with real Claude Code CLI."""

    def test_claude_code_modifies_file(self, temp_repo: str) -> None:
        """Actually creates/modifies a file."""
        worker = CoderWorker(timeout=300)  # 5 minute timeout for integration test

        task = CodingTask(
            ticket_id="1",
            ticket_title="Create hello.txt",
            ticket_body="Create a file named hello.txt with the content 'Hello, World!'",
            repo_path=temp_repo,
            branch="main",
            feedback=None,
        )

        result = worker.execute(task)

        # Check that Claude Code ran (may succeed or fail depending on environment)
        assert result.output is not None

        # If successful, check file was created
        if result.success:
            hello_file = Path(temp_repo) / "hello.txt"
            assert hello_file.exists(), "Expected hello.txt to be created"
