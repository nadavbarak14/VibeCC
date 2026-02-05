"""Claude Code CLI wrapper for LLM-based code generation."""

from __future__ import annotations

import logging
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from freespec.llm.session_logger import SessionLogger

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
    session_id: str | None = None


class ClaudeCodeClient:
    """Client for invoking Claude Code CLI.

    Wraps the claude CLI to generate code from prompts.
    """

    def __init__(
        self,
        timeout: int | None = None,
        working_dir: Path | str | None = None,
        log_dir: Path | str | None = None,
        stream_output: bool = False,
        session_logger: SessionLogger | None = None,
    ) -> None:
        """Initialize the Claude Code client.

        Args:
            timeout: Optional timeout in seconds for CLI execution.
            working_dir: Working directory for CLI commands.
            log_dir: Directory to save compilation logs. If None, no logs saved.
            stream_output: If True, print Claude output to stderr in real-time.
            session_logger: Optional session logger for comprehensive logging.
        """
        self.timeout = timeout
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()
        self.log_dir = Path(log_dir) if log_dir else None
        self.stream_output = stream_output
        self.session_logger = session_logger
        self.log_callback: Callable[[str], None] | None = None
        self._current_spec_id: str | None = None
        self._current_phase: str = "other"
        self._current_attempt: int | None = None

    def set_current_spec(self, spec_id: str) -> None:
        """Set the current spec being compiled (for log file naming)."""
        self._current_spec_id = spec_id
        if self.session_logger:
            self.session_logger.set_current_spec(spec_id)

    def set_current_phase(self, phase: str) -> None:
        """Set the current phase (header, impl, review, fix).

        Args:
            phase: The current compilation phase.
        """
        self._current_phase = phase
        if self.session_logger:
            self.session_logger.set_current_phase(phase)

    def set_current_attempt(self, attempt: int | None) -> None:
        """Set the current attempt number for retries.

        Args:
            attempt: The current attempt number, or None if not in a retry loop.
        """
        self._current_attempt = attempt

    def generate(self, prompt: str, session_id: str | None = None) -> GenerationResult:
        """Generate code using Claude Code CLI.

        Args:
            prompt: The prompt describing what to generate.
            session_id: Optional session ID to continue an existing conversation.
                If provided, uses --resume to continue the session.
                If None, creates a new session with a generated ID.

        Returns:
            GenerationResult with success status, output, and session_id for continuation.
        """
        return self._generate_internal(prompt, session_id, fork=False)

    def fork_session(self, session_id: str, prompt: str) -> GenerationResult:
        """Fork from an existing session and continue with new prompt.

        Creates a new session branching from the specified session point.
        The original session remains unchanged; a new session ID is generated
        for the fork.

        Args:
            session_id: Session ID to fork from.
            prompt: The prompt for the forked session.

        Returns:
            GenerationResult with success status, output, and new session_id for the fork.
        """
        return self._generate_internal(prompt, session_id, fork=True)

    def _generate_internal(
        self, prompt: str, session_id: str | None, fork: bool
    ) -> GenerationResult:
        """Internal method for code generation with optional forking.

        Args:
            prompt: The prompt describing what to generate.
            session_id: Session ID for resume or fork operations.
            fork: If True, fork from session_id instead of resuming.

        Returns:
            GenerationResult with success status, output, and session_id.
        """
        logger.debug("Generating with prompt (%d chars)", len(prompt))
        start_time = time.time()

        # For forking, we need a new session ID for the fork
        # For resume, we use the existing session ID
        # For new sessions, we generate a new ID
        if fork:
            # Fork creates a new session branching from the parent
            effective_session_id = str(uuid.uuid4())
            parent_session_id = session_id
        else:
            effective_session_id = session_id or str(uuid.uuid4())
            parent_session_id = None

        is_resume = session_id is not None and not fork

        # Determine interaction type for logging
        if fork:
            interaction_type = "fork"
        elif is_resume:
            interaction_type = "resume"
        else:
            interaction_type = "generate"

        try:
            result = self._run_claude(
                prompt, effective_session_id, is_resume, fork, parent_session_id
            )
            duration = time.time() - start_time
            result.duration_seconds = duration

            # Save logs if log_dir is configured
            if self.log_dir:
                log_file = self._save_log(prompt, result, duration)
                result.log_file = log_file

            # Log to session logger if configured
            if self.session_logger:
                self.session_logger.log_interaction(
                    interaction_type=interaction_type,
                    prompt=prompt,
                    output=result.output,
                    success=result.success,
                    error=result.error,
                    duration_seconds=duration,
                    session_id=effective_session_id,
                    parent_session_id=parent_session_id,
                    attempt=self._current_attempt,
                )

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
                session_id=effective_session_id,
            )
            if self.log_dir:
                result.log_file = self._save_log(prompt, result, duration)
            if self.session_logger:
                self.session_logger.log_interaction(
                    interaction_type=interaction_type,
                    prompt=prompt,
                    output=output,
                    success=False,
                    error=result.error,
                    duration_seconds=duration,
                    session_id=effective_session_id,
                    parent_session_id=parent_session_id,
                    attempt=self._current_attempt,
                )
            return result
        except FileNotFoundError:
            duration = time.time() - start_time
            logger.error("Claude Code CLI not found in PATH")
            result = GenerationResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Ensure 'claude' is installed and in PATH.",
                duration_seconds=duration,
                session_id=effective_session_id,
            )
            if self.log_dir:
                result.log_file = self._save_log(prompt, result, duration)
            if self.session_logger:
                self.session_logger.log_interaction(
                    interaction_type=interaction_type,
                    prompt=prompt,
                    output="",
                    success=False,
                    error=result.error,
                    duration_seconds=duration,
                    session_id=effective_session_id,
                    parent_session_id=parent_session_id,
                    attempt=self._current_attempt,
                )
            return result
        except OSError as e:
            duration = time.time() - start_time
            logger.error("Failed to execute Claude Code: %s", e)
            result = GenerationResult(
                success=False,
                output="",
                error=f"Failed to execute Claude Code: {e}",
                duration_seconds=duration,
                session_id=effective_session_id,
            )
            if self.log_dir:
                result.log_file = self._save_log(prompt, result, duration)
            if self.session_logger:
                self.session_logger.log_interaction(
                    interaction_type=interaction_type,
                    prompt=prompt,
                    output="",
                    success=False,
                    error=result.error,
                    duration_seconds=duration,
                    session_id=effective_session_id,
                    parent_session_id=parent_session_id,
                    attempt=self._current_attempt,
                )
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
            f.write(f"{'=' * 80}\n")
            f.write("FREESPEC COMPILATION LOG\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Spec: {self._current_spec_id or 'unknown'}\n")
            f.write(f"Duration: {duration:.2f} seconds\n")
            f.write(f"Success: {result.success}\n")
            if result.error:
                f.write(f"Error: {result.error}\n")
            f.write(f"\n{'=' * 80}\n")
            f.write(f"PROMPT ({len(prompt)} chars)\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(prompt)
            f.write(f"\n\n{'=' * 80}\n")
            f.write("CLAUDE CODE OUTPUT\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(result.output)
            f.write("\n")

        logger.info("Log saved to: %s", log_file)
        return log_file

    def _run_claude(
        self,
        prompt: str,
        session_id: str,
        is_resume: bool = False,
        is_fork: bool = False,
        parent_session_id: str | None = None,
    ) -> GenerationResult:
        """Run the Claude Code CLI subprocess.

        Args:
            prompt: The prompt to send.
            session_id: Session ID for the conversation (new ID for forks).
            is_resume: If True, resume an existing session.
            is_fork: If True, fork from parent_session_id.
            parent_session_id: Session to fork from (required if is_fork=True).

        Returns:
            GenerationResult based on execution.
        """
        if is_fork and parent_session_id:
            # Fork from existing session
            cmd = [
                "claude",
                "--resume",
                parent_session_id,
                "--fork-session",
                "-p",
                prompt,
                "--dangerously-skip-permissions",
            ]
        elif is_resume:
            # Continue existing session
            cmd = [
                "claude",
                "--resume",
                session_id,
                "-p",
                prompt,
                "--dangerously-skip-permissions",
            ]
        else:
            # New session with explicit ID
            cmd = [
                "claude",
                "--session-id",
                session_id,
                "-p",
                prompt,
                "--dangerously-skip-permissions",
            ]

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

                    if self.stream_output:
                        print(stripped_line, flush=True)

                    if self.log_callback:
                        self.log_callback(stripped_line)

            process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise

        output = "\n".join(output_lines)

        if process.returncode == 0:
            return GenerationResult(success=True, output=output, session_id=session_id)
        else:
            return GenerationResult(
                success=False,
                output=output,
                error=f"Claude Code exited with code {process.returncode}",
                session_id=session_id,
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
