"""Data models for workers."""

from dataclasses import dataclass


@dataclass
class CodingTask:
    """Input for a coding task.

    Attributes:
        ticket_id: Unique identifier for the ticket.
        ticket_title: Title/summary of the ticket.
        ticket_body: Full description/body of the ticket.
        repo_path: Path to the git repository.
        branch: Branch to work on.
        feedback: Optional feedback from previous CI failure.
    """

    ticket_id: str
    ticket_title: str
    ticket_body: str
    repo_path: str
    branch: str
    feedback: str | None = None


@dataclass
class CodingResult:
    """Result of a coding task.

    Attributes:
        success: Whether the task completed successfully.
        output: Claude Code output for logging.
        error: Error message if task failed.
    """

    success: bool
    output: str
    error: str | None = None
