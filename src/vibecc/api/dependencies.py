"""FastAPI dependencies for dependency injection."""

from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends

from vibecc.state_store import StateStore


@dataclass
class AutopilotStatus:
    """Status of the autopilot for a project."""

    project_id: str
    running: bool
    active_pipelines: int
    queued_tickets: int


class Orchestrator(Protocol):
    """Interface for the Orchestrator component."""

    def start_autopilot(self, project_id: str) -> None:
        """Start autopilot for a project."""
        ...

    def stop_autopilot(self, project_id: str) -> None:
        """Stop autopilot for a project."""
        ...

    def get_autopilot_status(self, project_id: str) -> AutopilotStatus:
        """Get autopilot status for a project."""
        ...


# Global StateStore instance (initialized on app startup)
_state_store: StateStore | None = None


def init_state_store(db_path: str = "vibecc.db") -> None:
    """Initialize the global StateStore instance."""
    global _state_store  # noqa: PLW0603
    _state_store = StateStore(db_path)


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
