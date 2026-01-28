"""Coder Worker - Claude Code CLI integration."""

from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from vibecc.workers.models import CodingResult, CodingTask

if TYPE_CHECKING:
    from subprocess import CompletedProcess

logger = logging.getLogger("vibecc.workers.coder")


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
        logger.info("Executing coding task for ticket #%s: %s", task.ticket_id, task.ticket_title)
        if task.feedback:
            logger.info("Task includes CI feedback from previous attempt")

        prompt = self.build_prompt(task)
        logger.debug("Built prompt (%d chars)", len(prompt))

        try:
            logger.info("Running Claude Code CLI...")
            result = self._run_claude_code(prompt, task.repo_path)
            coding_result = self._process_result(result)
            if coding_result.success:
                logger.info("Claude Code completed successfully")
            else:
                logger.error("Claude Code failed: %s", coding_result.error)
            logger.debug(
                "Output (%d chars): %s",
                len(coding_result.output),
                coding_result.output[:500] if coding_result.output else "(empty)",
            )
            return coding_result
        except subprocess.TimeoutExpired as e:
            logger.error("Claude Code timed out after %s seconds", self.timeout)
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
            logger.error("Claude Code CLI not found in PATH")
            return CodingResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Ensure 'claude' is installed and in PATH.",
            )
        except OSError as e:
            logger.error("Failed to execute Claude Code: %s", e)
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
