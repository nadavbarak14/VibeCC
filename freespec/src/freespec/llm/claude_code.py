"""Claude Code CLI wrapper for LLM-based code generation."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
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
    duration_seconds: float = 0.0
    log_file: Path | None = None


class ClaudeCodeClient:
    """Client for invoking Claude Code CLI.

    Wraps the claude CLI to generate code from prompts.
    """

    def __init__(
        self,
        timeout: int | None = None,
        working_dir: Path | str | None = None,
        log_dir: Path | str | None = None,
    ) -> None:
        """Initialize the Claude Code client.

        Args:
            timeout: Optional timeout in seconds for CLI execution.
            working_dir: Working directory for CLI commands.
            log_dir: Directory to save compilation logs. If None, no logs saved.
        """
        self.timeout = timeout
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.log_dir = Path(log_dir) if log_dir else None
        self.log_callback: Callable[[str], None] | None = None
        self._current_spec_id: str | None = None

    def set_current_spec(self, spec_id: str) -> None:
        """Set the current spec being compiled (for log file naming)."""
        self._current_spec_id = spec_id

    def generate(self, prompt: str) -> GenerationResult:
        """Generate code using Claude Code CLI.

        Args:
            prompt: The prompt describing what to generate.

        Returns:
            GenerationResult with success status and output.
        """
        logger.debug("Generating with prompt (%d chars)", len(prompt))
        start_time = time.time()

        try:
            result = self._run_claude(prompt)
            duration = time.time() - start_time
            result.duration_seconds = duration

            # Save logs if log_dir is configured
            if self.log_dir:
                log_file = self._save_log(prompt, result, duration)
                result.log_file = log_file

            return result
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            logger.error("Claude Code timed out after %s seconds", self.timeout)
            output = ""
            if e.stdout:
                output = (
                    e.stdout.decode("utf-8", errors="replace")
                    if isinstance(e.stdout, bytes)
                    else str(e.stdout)
                )
            result = GenerationResult(
                success=False,
                output=output,
                error=f"Claude Code timed out after {self.timeout} seconds",
                duration_seconds=duration,
            )
            if self.log_dir:
                result.log_file = self._save_log(prompt, result, duration)
            return result
        except FileNotFoundError:
            duration = time.time() - start_time
            logger.error("Claude Code CLI not found in PATH")
            result = GenerationResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Ensure 'claude' is installed and in PATH.",
                duration_seconds=duration,
            )
            if self.log_dir:
                result.log_file = self._save_log(prompt, result, duration)
            return result
        except OSError as e:
            duration = time.time() - start_time
            logger.error("Failed to execute Claude Code: %s", e)
            result = GenerationResult(
                success=False,
                output="",
                error=f"Failed to execute Claude Code: {e}",
                duration_seconds=duration,
            )
            if self.log_dir:
                result.log_file = self._save_log(prompt, result, duration)
            return result

    def _save_log(self, prompt: str, result: GenerationResult, duration: float) -> Path:
        """Save compilation log to disk.

        Args:
            prompt: The prompt sent to Claude Code.
            result: The generation result.
            duration: How long the generation took in seconds.

        Returns:
            Path to the saved log file.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        spec_name = self._current_spec_id.replace("/", "_") if self._current_spec_id else "unknown"
        status = "success" if result.success else "failed"
        log_filename = f"{timestamp}_{spec_name}_{status}.log"
        log_file = self.log_dir / log_filename

        with open(log_file, "w") as f:
            f.write(f"{'='*80}\n")
            f.write(f"FREESPEC COMPILATION LOG\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Spec: {self._current_spec_id or 'unknown'}\n")
            f.write(f"Duration: {duration:.2f} seconds\n")
            f.write(f"Success: {result.success}\n")
            if result.error:
                f.write(f"Error: {result.error}\n")
            f.write(f"\n{'='*80}\n")
            f.write(f"PROMPT ({len(prompt)} chars)\n")
            f.write(f"{'='*80}\n\n")
            f.write(prompt)
            f.write(f"\n\n{'='*80}\n")
            f.write(f"CLAUDE CODE OUTPUT\n")
            f.write(f"{'='*80}\n\n")
            f.write(result.output)
            f.write("\n")

        logger.info("Log saved to: %s", log_file)
        return log_file

    def _run_claude(self, prompt: str) -> GenerationResult:
        """Run the Claude Code CLI subprocess.

        Args:
            prompt: The prompt to send.

        Returns:
            GenerationResult based on execution.
        """
        cmd = ["claude", "-p", prompt, "--dangerously-skip-permissions"]

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
