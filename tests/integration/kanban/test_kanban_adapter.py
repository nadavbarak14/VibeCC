"""Integration tests for KanbanAdapter.

These tests require:
- GITHUB_TOKEN environment variable
- GITHUB_TEST_REPO environment variable (e.g., "owner/test-repo")
- GITHUB_TEST_PROJECT_NUMBER environment variable (project number)
- A GitHub Project with Queue/In Progress/Done/Failed columns
- At least one issue in the Queue column

Run with: pytest tests/integration/kanban/ -m real
"""

import os

import pytest

from vibecc.kanban import KanbanAdapter, Ticket

# Skip all tests in this module if credentials not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.real,
    pytest.mark.skipif(
        not os.environ.get("GITHUB_TOKEN")
        or not os.environ.get("GITHUB_TEST_REPO")
        or not os.environ.get("GITHUB_TEST_PROJECT_NUMBER"),
        reason="GITHUB_TOKEN, GITHUB_TEST_REPO, and GITHUB_TEST_PROJECT_NUMBER required",
    ),
]


@pytest.fixture
def github_token() -> str:
    """Get GitHub token from environment."""
    return os.environ["GITHUB_TOKEN"]


@pytest.fixture
def test_repo() -> str:
    """Get test repo from environment."""
    return os.environ["GITHUB_TEST_REPO"]


@pytest.fixture
def project_number() -> int:
    """Get test project number from environment."""
    return int(os.environ["GITHUB_TEST_PROJECT_NUMBER"])


@pytest.fixture
def adapter(test_repo: str, project_number: int, github_token: str) -> KanbanAdapter:
    """Create a KanbanAdapter for the test project."""
    adapter = KanbanAdapter(
        repo=test_repo,
        project_number=project_number,
        token=github_token,
    )
    yield adapter
    adapter.close()


class TestListAndMoveTicket:
    """Integration test for listing and moving tickets."""

    def test_list_and_move_ticket(self, adapter: KanbanAdapter) -> None:
        """List from Queue -> move to In Progress -> verify -> move back."""
        # 1. List tickets in Queue
        queue_tickets = adapter.list_tickets("queue")

        # Skip if no tickets in queue
        if not queue_tickets:
            pytest.skip("No tickets in Queue column to test with")

        ticket = queue_tickets[0]
        assert isinstance(ticket, Ticket)
        assert ticket.id
        assert ticket.title

        # 2. Move to In Progress
        adapter.move_ticket(ticket.id, "in_progress")

        # 3. Verify ticket is now in In Progress
        in_progress_tickets = adapter.list_tickets("in_progress")
        in_progress_ids = [t.id for t in in_progress_tickets]
        assert ticket.id in in_progress_ids

        # 4. Move back to Queue (cleanup)
        adapter.move_ticket(ticket.id, "queue")

        # 5. Verify ticket is back in Queue
        queue_tickets_after = adapter.list_tickets("queue")
        queue_ids = [t.id for t in queue_tickets_after]
        assert ticket.id in queue_ids
