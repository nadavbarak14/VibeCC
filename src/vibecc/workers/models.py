"""Data models for workers."""

from dataclasses import dataclass

from vibecc.git_manager.models import CIStatus


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


@dataclass
class TestingTask:
    """Input for a testing task.

    Attributes:
        ticket_id: Unique identifier for the ticket.
        ticket_title: Title/summary of the ticket.
        branch: Branch to push and create PR from.
        repo_path: Path to the git repository.
    """

    ticket_id: str
    ticket_title: str
    branch: str
    repo_path: str


@dataclass
class TestingResult:
    """Result of a testing task.

    Attributes:
        success: Whether CI passed.
        pr_id: GitHub PR ID.
        pr_url: URL to the pull request.
        ci_status: Final CI status.
        failure_logs: CI failure info for feedback (if CI failed).
    """

    success: bool
    pr_id: int
    pr_url: str
    ci_status: CIStatus
    failure_logs: str | None = None
