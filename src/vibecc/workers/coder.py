"""Coder Worker - Claude Code CLI integration."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from vibecc.workers.models import CodingResult, CodingTask

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("vibecc.workers.coder")


@dataclass
class StreamingResult:
    """Result from streaming subprocess execution."""

    returncode: int
    output: str


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
        self.log_callback: Callable[[str], None] | None = None

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
            prompt_parts.extend(
                [
                    "",
                    "## Previous CI Feedback",
                    "",
                    "The CI pipeline failed on a previous attempt. Fix the following issues:",
                    "",
                    task.feedback,
                ]
            )

        prompt_parts.extend(
            [
                "",
                "## Instructions",
                "",
                "1. Complete this ticket by modifying the necessary files",
                "2. After making all changes, commit them with a descriptive message",
                f"3. Reference ticket number in commit (e.g., '#{task.ticket_id}')",
            ]
        )

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

    def _run_claude_code(self, prompt: str, repo_path: str) -> StreamingResult:
        """Run the Claude Code CLI subprocess with streaming output.

        Args:
            prompt: The prompt to send to Claude Code.
            repo_path: Working directory for the subprocess.

        Returns:
            StreamingResult with return code and collected output.
        """
        cmd = ["claude", "-p", prompt, "--permission-mode", "acceptEdits"]

        # Use Popen for streaming output
        process = subprocess.Popen(
            cmd,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified streaming
            text=True,
            bufsize=1,  # Line buffered
        )

        output_lines: list[str] = []
        try:
            # Stream output line by line
            if process.stdout:
                for raw_line in process.stdout:
                    stripped_line = raw_line.rstrip("\n")
                    output_lines.append(stripped_line)

                    # Call log callback if set
                    if self.log_callback:
                        self.log_callback(stripped_line)

            # Wait for process to complete
            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise

        return StreamingResult(
            returncode=process.returncode or 0,
            output="\n".join(output_lines),
        )

    def _process_result(self, result: StreamingResult) -> CodingResult:
        """Process the subprocess result into a CodingResult.

        Args:
            result: The streaming subprocess result.

        Returns:
            CodingResult based on exit code and output.
        """
        if result.returncode == 0:
            return CodingResult(success=True, output=result.output, error=None)
        else:
            return CodingResult(
                success=False,
                output=result.output,
                error=f"Claude Code exited with code {result.returncode}",
            )
