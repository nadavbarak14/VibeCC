"""Scheduler - Processes tickets from Queue into pipelines."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from vibecc.scheduler.models import SyncResult
from vibecc.state_store import PipelineState

if TYPE_CHECKING:
    from vibecc.git_manager import GitManager
    from vibecc.kanban import KanbanAdapter
    from vibecc.orchestrator import Orchestrator
    from vibecc.state_store import StateStore

logger = logging.getLogger(__name__)

# Active (non-terminal) pipeline states
_ACTIVE_STATES = [
    PipelineState.QUEUED,
    PipelineState.CODING,
    PipelineState.TESTING,
    PipelineState.REVIEW,
]


class Scheduler:
    """Processes tickets from Kanban queue into pipelines.

    Phase 1 is manual-only: the user clicks a button which calls sync()
    to process queued tickets up to available capacity.
    """

    def __init__(
        self,
        state_store: StateStore,
        orchestrator: Orchestrator,
        max_concurrent: int = 1,
    ) -> None:
        """Initialize the Scheduler.

        Args:
            state_store: StateStore instance for checking active pipelines.
            orchestrator: Orchestrator for starting pipelines.
            max_concurrent: Maximum concurrent pipelines per project.
        """
        self.state_store = state_store
        self.orchestrator = orchestrator
        self.max_concurrent = max_concurrent

    def sync(
        self,
        project_id: str,
        kanban: KanbanAdapter,
        git_manager: GitManager,
    ) -> SyncResult:
        """Process the queue once, starting pipelines up to available capacity.

        Args:
            project_id: The project to sync.
            kanban: KanbanAdapter for listing/moving tickets.
            git_manager: GitManager for branch creation (passed to orchestrator).

        Returns:
            SyncResult with started pipelines and remaining ticket count.
        """
        # Verify project exists
        self.state_store.get_project(project_id)

        # Get tickets from queue
        tickets = kanban.list_tickets("queue")
        logger.info("Found %d tickets in queue for project %s", len(tickets), project_id)

        if not tickets:
            return SyncResult(started=[], remaining=0)

        # Count active pipelines
        active_count = 0
        for state in _ACTIVE_STATES:
            active_count += len(self.state_store.list_pipelines(project_id=project_id, state=state))

        available_capacity = max(0, self.max_concurrent - active_count)
        logger.info(
            "Active: %d, capacity: %d, available: %d",
            active_count,
            self.max_concurrent,
            available_capacity,
        )

        if available_capacity == 0:
            return SyncResult(started=[], remaining=len(tickets))

        # Start pipelines for available tickets
        started = []
        for ticket in tickets[:available_capacity]:
            logger.info("Starting pipeline for ticket #%s", ticket.id)
            pipeline = self.orchestrator.start_pipeline(project_id, ticket, git_manager)
            kanban.move_ticket(ticket.id, "in_progress")
            started.append(pipeline)

        remaining = len(tickets) - len(started)
        logger.info("Sync complete: started %d, remaining %d", len(started), remaining)

        return SyncResult(started=started, remaining=remaining)
