"""Claude Code CLI wrapper for LLM-based code generation."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("freespec.llm")


class ClaudeCodeError(Exception):
    """Raised when Claude Code execution fails."""


@dataclass
class GenerationResult:
    """Result from Claude Code generation."""

    success: bool
    output: str
    error: str | None = None


class ClaudeCodeClient:
    """Client for invoking Claude Code CLI.

    Wraps the claude CLI to generate code from prompts.
    """

    def __init__(
        self,
        timeout: int | None = None,
        working_dir: Path | str | None = None,
    ) -> None:
        """Initialize the Claude Code client.

        Args:
            timeout: Optional timeout in seconds for CLI execution.
            working_dir: Working directory for CLI commands.
        """
        self.timeout = timeout
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.log_callback: Callable[[str], None] | None = None

    def generate(self, prompt: str) -> GenerationResult:
        """Generate code using Claude Code CLI.

        Args:
            prompt: The prompt describing what to generate.

        Returns:
            GenerationResult with success status and output.
        """
        logger.debug("Generating with prompt (%d chars)", len(prompt))

        try:
            result = self._run_claude(prompt)
            return result
        except subprocess.TimeoutExpired as e:
            logger.error("Claude Code timed out after %s seconds", self.timeout)
            output = ""
            if e.stdout:
                output = (
                    e.stdout.decode("utf-8", errors="replace")
                    if isinstance(e.stdout, bytes)
                    else str(e.stdout)
                )
            return GenerationResult(
                success=False,
                output=output,
                error=f"Claude Code timed out after {self.timeout} seconds",
            )
        except FileNotFoundError:
            logger.error("Claude Code CLI not found in PATH")
            return GenerationResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Ensure 'claude' is installed and in PATH.",
            )
        except OSError as e:
            logger.error("Failed to execute Claude Code: %s", e)
            return GenerationResult(
                success=False,
                output="",
                error=f"Failed to execute Claude Code: {e}",
            )

    def _run_claude(self, prompt: str) -> GenerationResult:
        """Run the Claude Code CLI subprocess.

        Args:
            prompt: The prompt to send.

        Returns:
            GenerationResult based on execution.
        """
        cmd = ["claude", "-p", prompt, "--permission-mode", "acceptEdits"]

        process = subprocess.Popen(
            cmd,
            cwd=self.working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        output_lines: list[str] = []
        try:
            if process.stdout:
                for raw_line in process.stdout:
                    stripped_line = raw_line.rstrip("\n")
                    output_lines.append(stripped_line)

                    if self.log_callback:
                        self.log_callback(stripped_line)

            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise

        output = "\n".join(output_lines)

        if process.returncode == 0:
            return GenerationResult(success=True, output=output)
        else:
            return GenerationResult(
                success=False,
                output=output,
                error=f"Claude Code exited with code {process.returncode}",
            )

    def check_available(self) -> bool:
        """Check if Claude Code CLI is available.

        Returns:
            True if claude CLI is found and responds.
        """
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
