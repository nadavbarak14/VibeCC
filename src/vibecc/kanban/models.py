"""Data models for Kanban Adapter."""

from dataclasses import dataclass, field


@dataclass
class Ticket:
    """Represents a ticket/issue from GitHub Projects."""

    id: str  # GitHub issue number
    title: str
    body: str
    labels: list[str] = field(default_factory=list)
