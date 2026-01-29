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

# Working states - pipelines actively being processed (not queued)
_WORKING_STATES = [
    PipelineState.CODING,
    PipelineState.TESTING,
    PipelineState.REVIEW,
]


class Scheduler:
    """Processes tickets from Kanban queue into pipelines.

    Sync pulls ALL tickets from GitHub into the QUEUED state (unlimited queue).
    max_concurrent only limits how many can be in CODING/TESTING/REVIEW at once.
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
            max_concurrent: Maximum concurrent working pipelines per project.
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
        """Pull all tickets from GitHub queue into pipelines.

        Pulls ALL tickets from GitHub "Todo" column into QUEUED state.
        The queue can be unlimited - max_concurrent only limits working pipelines.

        Args:
            project_id: The project to sync.
            kanban: KanbanAdapter for listing/moving tickets.
            git_manager: GitManager for branch creation (passed to orchestrator).

        Returns:
            SyncResult with started pipelines and remaining ticket count.
        """
        # Verify project exists
        self.state_store.get_project(project_id)

        # Get tickets from GitHub queue
        tickets = kanban.list_tickets("queue")
        logger.info("Found %d tickets in GitHub queue for project %s", len(tickets), project_id)

        if not tickets:
            return SyncResult(started=[], remaining=0)

        # Pull ALL tickets into QUEUED state (unlimited queue)
        started = []
        for ticket in tickets:
            logger.info("Creating pipeline for ticket #%s", ticket.id)
            pipeline = self.orchestrator.start_pipeline(project_id, ticket, git_manager)
            kanban.move_ticket(ticket.id, "in_progress")
            started.append(pipeline)

        logger.info("Sync complete: pulled %d tickets into queue", len(started))

        return SyncResult(started=started, remaining=0)
