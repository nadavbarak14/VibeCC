"""Coder Worker - Claude Code CLI integration."""

from __future__ import annotations

import logging
import subprocess
import threading
from collections.abc import Callable

from vibecc.workers.models import CodingResult, CodingTask

logger = logging.getLogger("vibecc.workers.coder")


class CoderWorker:
    """Worker that invokes Claude Code CLI for coding tasks.

    Builds a prompt from ticket information and invokes the Claude Code CLI
    to complete the coding task. Streams output in real-time and detects
    success/failure from the exit code.
    """

    def __init__(
        self,
        timeout: int | None = None,
        auto_commit: bool = True,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the Coder Worker.

        Args:
            timeout: Optional timeout in seconds for Claude Code execution.
                     None means no timeout (default for phase 1).
            auto_commit: If True, instruct Claude to commit changes after editing.
            log_callback: Optional callback to stream log lines in real-time.
        """
        self.timeout = timeout
        self.auto_commit = auto_commit
        self.log_callback = log_callback

    def build_prompt(self, task: CodingTask) -> str:
        """Build the prompt for Claude Code from task information."""
        prompt_parts = [
            f"You are working on ticket #{task.ticket_id}: {task.ticket_title}",
            "",
            task.ticket_body,
        ]

        if task.feedback:
            prompt_parts.extend(["", "## Previous CI Feedback", "", task.feedback])

        prompt_parts.extend(["", "Complete this ticket by modifying the necessary files."])

        if self.auto_commit:
            prompt_parts.extend([
                "",
                "IMPORTANT: After making all changes, you MUST commit them with a descriptive message.",
                f"Use: git add -A && git commit -m '#{task.ticket_id}: <brief description>'",
            ])

        return "\n".join(prompt_parts)

    def execute(self, task: CodingTask) -> CodingResult:
        """Execute a coding task using Claude Code CLI."""
        logger.info("Executing coding task for ticket #%s: %s", task.ticket_id, task.ticket_title)
        if task.feedback:
            logger.info("Task includes CI feedback from previous attempt")

        prompt = self.build_prompt(task)
        logger.debug("Built prompt (%d chars)", len(prompt))

        try:
            logger.info("Running Claude Code CLI...")
            return self._run_claude_code(prompt, task.repo_path)
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

    def _run_claude_code(self, prompt: str, repo_path: str) -> CodingResult:
        """Run the Claude Code CLI subprocess with streaming output."""
        cmd = ["claude", "-p", prompt, "--permission-mode", "acceptEdits"]
        if self.auto_commit:
            cmd.extend(["--allowedTools", "Bash(git:*)"])

        output_lines: list[str] = []

        process = subprocess.Popen(
            cmd,
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def read_output() -> None:
            if process.stdout:
                for line in process.stdout:
                    line = line.rstrip("\n")
                    output_lines.append(line)
                    logger.debug("Claude: %s", line)
                    if self.log_callback:
                        self.log_callback(line)

        reader_thread = threading.Thread(target=read_output)
        reader_thread.start()

        try:
            process.wait(timeout=self.timeout)
            reader_thread.join(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            reader_thread.join(timeout=5)
            return CodingResult(
                success=False,
                output="\n".join(output_lines),
                error=f"Claude Code timed out after {self.timeout} seconds",
            )

        output = "\n".join(output_lines)

        if process.returncode == 0:
            logger.info("Claude Code completed successfully")
            return CodingResult(success=True, output=output, error=None)
        else:
            logger.error("Claude Code exited with code %d", process.returncode)
            return CodingResult(
                success=False,
                output=output,
                error=f"Claude Code exited with code {process.returncode}",
            )
