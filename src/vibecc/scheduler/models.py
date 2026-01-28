"""Data models for the Scheduler module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibecc.state_store import Pipeline


@dataclass
class SyncResult:
    """Result of a sync operation.

    Attributes:
        started: Pipelines that were started during this sync.
        remaining: Number of tickets still in queue after sync.
    """

    started: list[Pipeline] = field(default_factory=list)
    remaining: int = 0
