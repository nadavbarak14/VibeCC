"""Coder Worker - Claude Code CLI integration."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from vibecc.workers.models import CodingResult, CodingTask

if TYPE_CHECKING:
    from subprocess import CompletedProcess


class CoderWorker:
    """Worker that invokes Claude Code CLI for coding tasks.

    Builds a prompt from ticket information and invokes the Claude Code CLI
    to complete the coding task. Captures output for logging and detects
    success/failure from the exit code.
    """

    def __init__(self, timeout: int | None = None) -> None:
        """Initialize the Coder Worker.

        Args:
            timeout: Optional timeout in seconds for Claude Code execution.
                     None means no timeout (default for phase 1).
        """
        self.timeout = timeout

    def build_prompt(self, task: CodingTask) -> str:
        """Build the prompt for Claude Code from task information.

        Args:
            task: The coding task with ticket information.

        Returns:
            Formatted prompt string for Claude Code.
        """
        prompt_parts = [
            f"You are working on ticket #{task.ticket_id}: {task.ticket_title}",
            "",
            task.ticket_body,
        ]

        if task.feedback:
            prompt_parts.extend(["", "## Previous CI Feedback", "", task.feedback])

        prompt_parts.extend(["", "Complete this ticket by modifying the necessary files."])

        return "\n".join(prompt_parts)

    def execute(self, task: CodingTask) -> CodingResult:
        """Execute a coding task using Claude Code CLI.

        Args:
            task: The coding task to execute.

        Returns:
            CodingResult with success status and output.
        """
        prompt = self.build_prompt(task)

        try:
            result = self._run_claude_code(prompt, task.repo_path)
            return self._process_result(result)
        except subprocess.TimeoutExpired as e:
            output = ""
            if e.stdout:
                output = (
                    e.stdout.decode("utf-8", errors="replace")
                    if isinstance(e.stdout, bytes)
                    else str(e.stdout)
                )
            return CodingResult(
                success=False,
                output=output,
                error=f"Claude Code timed out after {self.timeout} seconds",
            )
        except FileNotFoundError:
            return CodingResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Ensure 'claude' is installed and in PATH.",
            )
        except OSError as e:
            return CodingResult(
                success=False,
                output="",
                error=f"Failed to execute Claude Code: {e}",
            )

    def _run_claude_code(self, prompt: str, repo_path: str) -> CompletedProcess[str]:
        """Run the Claude Code CLI subprocess.

        Args:
            prompt: The prompt to send to Claude Code.
            repo_path: Working directory for the subprocess.

        Returns:
            CompletedProcess with stdout/stderr.
        """
        return subprocess.run(
            ["claude", "-p", prompt, "--permission-mode", "acceptEdits"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=False,
        )

    def _process_result(self, result: CompletedProcess[str]) -> CodingResult:
        """Process the subprocess result into a CodingResult.

        Args:
            result: The completed subprocess result.

        Returns:
            CodingResult based on exit code and output.
        """
        # Combine stdout and stderr for complete output
        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(result.stderr)
        output = "\n".join(output_parts)

        if result.returncode == 0:
            return CodingResult(success=True, output=output, error=None)
        else:
            return CodingResult(
                success=False,
                output=output,
                error=f"Claude Code exited with code {result.returncode}",
            )
