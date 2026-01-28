"""FastAPI dependencies for dependency injection."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends

from vibecc.state_store import StateStore

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
