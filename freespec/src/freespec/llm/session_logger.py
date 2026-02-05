"""Session-level logging for Claude Code interactions.

Captures all LLM interactions in a single log file per compilation session,
making it easy to investigate what happened during a build.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class InteractionRecord:
    """A single interaction with Claude Code."""

    timestamp: str
    interaction_type: str  # 'generate', 'fork', 'resume'
    phase: str  # 'header', 'impl', 'review', 'fix', 'other'
    spec_id: str | None
    prompt: str
    output: str
    success: bool
    error: str | None
    duration_seconds: float
    session_id: str | None
    parent_session_id: str | None = None
    attempt: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SessionLog:
    """Complete log of a compilation session."""

    session_start: str
    project_name: str
    language: str
    interactions: list[InteractionRecord] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_start": self.session_start,
            "project_name": self.project_name,
            "language": self.language,
            "interactions": [i.to_dict() for i in self.interactions],
            "summary": self.summary,
        }


class SessionLogger:
    """Logs all Claude Code interactions for a compilation session.

    Creates two log files:
    - {timestamp}_session.log: Human-readable log with full prompts/outputs
    - {timestamp}_session.json: Structured JSON for programmatic analysis
    """

    def __init__(
        self,
        log_dir: Path,
        project_name: str,
        language: str,
    ) -> None:
        """Initialize the session logger.

        Args:
            log_dir: Directory to write logs to.
            project_name: Name of the project being compiled.
            language: Target language (python, cpp).
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.session_start = datetime.now(timezone.utc)
        timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")

        self.text_log_path = self.log_dir / f"{timestamp}_session.log"
        self.json_log_path = self.log_dir / f"{timestamp}_session.json"

        self.session_log = SessionLog(
            session_start=self.session_start.isoformat(),
            project_name=project_name,
            language=language,
        )

        self._interaction_count = 0
        self._current_spec_id: str | None = None
        self._current_phase: str = "other"
        self._write_lock = threading.Lock()

        # Write initial header to text log
        self._write_text_header()

    def _write_text_header(self) -> None:
        """Write the header to the text log file."""
        with open(self.text_log_path, "w") as f:
            f.write("=" * 100 + "\n")
            f.write("FREESPEC COMPILATION SESSION LOG\n")
            f.write("=" * 100 + "\n\n")
            f.write(f"Session Start: {self.session_start.isoformat()}\n")
            f.write(f"Project: {self.session_log.project_name}\n")
            f.write(f"Language: {self.session_log.language}\n")
            f.write(f"Text Log: {self.text_log_path}\n")
            f.write(f"JSON Log: {self.json_log_path}\n")
            f.write("\n" + "=" * 100 + "\n\n")

    def set_current_spec(self, spec_id: str) -> None:
        """Set the current spec being processed."""
        self._current_spec_id = spec_id

    def set_current_phase(self, phase: str) -> None:
        """Set the current phase (header, impl, review, fix)."""
        self._current_phase = phase

    def log_interaction(
        self,
        interaction_type: str,
        prompt: str,
        output: str,
        success: bool,
        error: str | None,
        duration_seconds: float,
        session_id: str | None,
        parent_session_id: str | None = None,
        attempt: int | None = None,
        metadata: dict[str, Any] | None = None,
        spec_id: str | None = None,
        phase: str | None = None,
    ) -> None:
        """Log a single interaction with Claude Code.

        Args:
            interaction_type: Type of interaction (generate, fork, resume).
            prompt: The prompt sent to Claude.
            output: The output received from Claude.
            success: Whether the interaction succeeded.
            error: Error message if failed.
            duration_seconds: How long the interaction took.
            session_id: The session ID used.
            parent_session_id: Parent session ID for forks.
            attempt: Attempt number for retries.
            metadata: Additional metadata to log.
            spec_id: Override spec_id (for thread-safe logging).
            phase: Override phase (for thread-safe logging).
        """
        with self._write_lock:
            self._interaction_count += 1

            record = InteractionRecord(
                timestamp=datetime.now(timezone.utc).isoformat(),
                interaction_type=interaction_type,
                phase=phase if phase is not None else self._current_phase,
                spec_id=spec_id if spec_id is not None else self._current_spec_id,
                prompt=prompt,
                output=output,
                success=success,
                error=error,
                duration_seconds=duration_seconds,
                session_id=session_id,
                parent_session_id=parent_session_id,
                attempt=attempt,
                metadata=metadata or {},
            )

            self.session_log.interactions.append(record)

            # Append to text log
            self._append_text_log(record)

            # Update JSON log (rewrite entire file for atomicity)
            self._save_json_log()

    def _append_text_log(self, record: InteractionRecord) -> None:
        """Append an interaction record to the text log."""
        with open(self.text_log_path, "a") as f:
            f.write(f"\n{'#' * 100}\n")
            f.write(f"INTERACTION #{self._interaction_count}\n")
            f.write(f"{'#' * 100}\n\n")

            f.write(f"Timestamp:    {record.timestamp}\n")
            f.write(f"Type:         {record.interaction_type}\n")
            f.write(f"Phase:        {record.phase}\n")
            f.write(f"Spec:         {record.spec_id or 'N/A'}\n")
            f.write(f"Session ID:   {record.session_id or 'N/A'}\n")
            if record.parent_session_id:
                f.write(f"Parent Sess:  {record.parent_session_id}\n")
            if record.attempt is not None:
                f.write(f"Attempt:      {record.attempt}\n")
            f.write(f"Duration:     {record.duration_seconds:.2f}s\n")
            f.write(f"Success:      {record.success}\n")
            if record.error:
                f.write(f"Error:        {record.error}\n")
            if record.metadata:
                f.write(f"Metadata:     {json.dumps(record.metadata)}\n")

            f.write(f"\n{'-' * 50}\n")
            f.write("PROMPT:\n")
            f.write(f"{'-' * 50}\n\n")
            f.write(record.prompt)
            f.write(f"\n\n{'-' * 50}\n")
            f.write("OUTPUT:\n")
            f.write(f"{'-' * 50}\n\n")
            f.write(record.output)
            f.write("\n")

    def _save_json_log(self) -> None:
        """Save the complete session log to JSON."""
        with open(self.json_log_path, "w") as f:
            json.dump(self.session_log.to_dict(), f, indent=2)

    def log_summary(
        self,
        total_specs: int,
        successful_specs: int,
        failed_specs: int,
        total_duration_seconds: float,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Log the final summary of the compilation session.

        Args:
            total_specs: Total number of specs processed.
            successful_specs: Number of specs that compiled successfully.
            failed_specs: Number of specs that failed.
            total_duration_seconds: Total duration of the session.
            extra: Additional summary data.
        """
        with self._write_lock:
            self.session_log.summary = {
                "session_end": datetime.now(timezone.utc).isoformat(),
                "total_specs": total_specs,
                "successful_specs": successful_specs,
                "failed_specs": failed_specs,
                "total_interactions": self._interaction_count,
                "total_duration_seconds": total_duration_seconds,
                **(extra or {}),
            }

            # Write summary to text log
            with open(self.text_log_path, "a") as f:
                f.write(f"\n{'=' * 100}\n")
                f.write("SESSION SUMMARY\n")
                f.write(f"{'=' * 100}\n\n")
                f.write(f"Session End:        {self.session_log.summary['session_end']}\n")
                f.write(f"Total Specs:        {total_specs}\n")
                f.write(f"Successful:         {successful_specs}\n")
                f.write(f"Failed:             {failed_specs}\n")
                f.write(f"Total Interactions: {self._interaction_count}\n")
                f.write(f"Total Duration:     {total_duration_seconds:.2f}s\n")
                if extra:
                    for key, value in extra.items():
                        f.write(f"{key}: {value}\n")
                f.write("\n")

            # Save final JSON
            self._save_json_log()

    def get_log_paths(self) -> tuple[Path, Path]:
        """Get the paths to the log files.

        Returns:
            Tuple of (text_log_path, json_log_path).
        """
        return self.text_log_path, self.json_log_path
