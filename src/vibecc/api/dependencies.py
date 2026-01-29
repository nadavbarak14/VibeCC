"""FastAPI dependencies for dependency injection."""

from __future__ import annotations

from collections.abc import Generator  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends

from vibecc.orchestrator.models import AutopilotStatus
from vibecc.state_store import StateStore

if TYPE_CHECKING:
    from vibecc.api.events import EventManager
    from vibecc.scheduler import SyncResult

# Re-export for backwards compatibility
__all__ = ["AutopilotStatus"]


class Orchestrator(Protocol):
    """Interface for the Orchestrator component."""

    def start_autopilot(self, project_id: str) -> None:
        """Start autopilot for a project."""
        ...

    def stop_autopilot(self, project_id: str, reason: str = ...) -> None:
        """Stop autopilot for a project."""
        ...

    def get_autopilot_status(self, project_id: str) -> AutopilotStatus:
        """Get autopilot status for a project."""
        ...


# Global StateStore instance (initialized on app startup)
_state_store: StateStore | None = None


def init_state_store(db_path: str = "vibecc.db") -> StateStore:
    """Initialize the global StateStore instance."""
    global _state_store  # noqa: PLW0603
    _state_store = StateStore(db_path)
    return _state_store


def close_state_store() -> None:
    """Close the global StateStore instance."""
    global _state_store  # noqa: PLW0603
    if _state_store is not None:
        _state_store.close()
        _state_store = None


def get_state_store() -> Generator[StateStore, None, None]:
    """Dependency that provides the StateStore instance."""
    if _state_store is None:
        raise RuntimeError("StateStore not initialized. Call init_state_store() first.")
    yield _state_store


# Type alias for dependency injection
StateStoreDep = Annotated[StateStore, Depends(get_state_store)]

# Global Orchestrator instance (initialized on app startup)
_orchestrator: Orchestrator | None = None


def init_orchestrator(orchestrator: Orchestrator) -> None:
    """Initialize the global Orchestrator instance."""
    global _orchestrator  # noqa: PLW0603
    _orchestrator = orchestrator


def close_orchestrator() -> None:
    """Close the global Orchestrator instance."""
    global _orchestrator  # noqa: PLW0603
    _orchestrator = None


def get_orchestrator() -> Generator[Orchestrator, None, None]:
    """Dependency that provides the Orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized. Call init_orchestrator() first.")
    yield _orchestrator


# Type alias for dependency injection
OrchestratorDep = Annotated[Orchestrator, Depends(get_orchestrator)]

# Global EventManager instance
_event_manager: EventManager | None = None


def init_event_manager() -> EventManager:
    """Initialize the global EventManager instance."""
    from vibecc.api.events import EventManager as EM  # noqa: PLC0415

    global _event_manager  # noqa: PLW0603
    _event_manager = EM()
    return _event_manager


def get_event_manager() -> Generator[EventManager, None, None]:
    """Dependency that provides the EventManager instance."""
    if _event_manager is None:
        raise RuntimeError("EventManager not initialized. Call init_event_manager() first.")
    yield _event_manager


def _get_event_manager_dep() -> Generator[EventManager, None, None]:
    """Dependency wrapper for EventManager."""
    yield from get_event_manager()


# Type alias for dependency injection
EventManagerDep = Annotated["EventManager", Depends(_get_event_manager_dep)]


class SchedulerProtocol(Protocol):
    """Interface for the Scheduler component."""

    def sync(self, project_id: str) -> SyncResult:
        """Process queue once, starting pipelines up to available capacity."""
        ...


# Global Scheduler instance (initialized on app startup)
_scheduler: SchedulerProtocol | None = None


def init_scheduler(scheduler: SchedulerProtocol) -> None:
    """Initialize the global Scheduler instance."""
    global _scheduler  # noqa: PLW0603
    _scheduler = scheduler


def close_scheduler() -> None:
    """Close the global Scheduler instance."""
    global _scheduler  # noqa: PLW0603
    _scheduler = None


def get_scheduler() -> Generator[SchedulerProtocol, None, None]:
    """Dependency that provides the Scheduler instance."""
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    yield _scheduler


# Type alias for dependency injection
SchedulerDep = Annotated[SchedulerProtocol, Depends(get_scheduler)]
