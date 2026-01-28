"""Data models for the Orchestrator module."""

from dataclasses import dataclass


@dataclass
class AutopilotStatus:
    """Status of autopilot for a project.

    Attributes:
        project_id: The project's unique ID.
        running: Whether autopilot is currently running.
        active_pipelines: Count of non-terminal pipelines.
        queued_tickets: Count of tickets in queue column.
    """

    project_id: str
    running: bool
    active_pipelines: int
    queued_tickets: int
