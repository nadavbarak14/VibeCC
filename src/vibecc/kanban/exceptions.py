"""Custom exceptions for Kanban Adapter."""


class KanbanError(Exception):
    """Base exception for Kanban Adapter errors."""


class TicketNotFoundError(KanbanError):
    """Ticket with given ID does not exist."""


class ColumnNotFoundError(KanbanError):
    """Column with given name does not exist."""


class ProjectNotFoundError(KanbanError):
    """GitHub Project not found."""
