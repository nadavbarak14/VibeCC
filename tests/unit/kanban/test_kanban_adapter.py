"""Unit tests for KanbanAdapter."""

from unittest.mock import MagicMock

import pytest

from vibecc.kanban import (
    ColumnNotFoundError,
    KanbanAdapter,
    Ticket,
    TicketNotFoundError,
)


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock HTTP client."""
    return MagicMock()


@pytest.fixture
def adapter(mock_client: MagicMock) -> KanbanAdapter:
    """Create a KanbanAdapter instance with mocked client."""
    adapter = KanbanAdapter(
        repo="owner/repo",
        project_number=1,
        token="test-token",
    )
    adapter._client = mock_client
    # Pre-populate project metadata to avoid extra GraphQL calls
    adapter._project_id = "PVT_123"
    adapter._status_field_id = "PVTSSF_456"
    adapter._column_options = {
        "Queue": "opt_queue",
        "In Progress": "opt_in_progress",
        "Done": "opt_done",
        "Failed": "opt_failed",
    }
    return adapter


def _mock_response(data: dict) -> MagicMock:
    """Create a mock GraphQL response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"data": data}
    return response


@pytest.mark.unit
class TestListTickets:
    """Tests for list_tickets."""

    def test_list_tickets_returns_tickets(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Returns list of Ticket objects."""
        mock_client.post.return_value = _mock_response(
            {
                "node": {
                    "items": {
                        "nodes": [
                            {
                                "id": "item_1",
                                "fieldValueByName": {"name": "Queue"},
                                "content": {
                                    "number": 42,
                                    "title": "Test ticket",
                                    "body": "Test body",
                                    "labels": {"nodes": [{"name": "bug"}]},
                                },
                            },
                            {
                                "id": "item_2",
                                "fieldValueByName": {"name": "Queue"},
                                "content": {
                                    "number": 43,
                                    "title": "Another ticket",
                                    "body": "Another body",
                                    "labels": {"nodes": []},
                                },
                            },
                        ]
                    }
                }
            }
        )

        tickets = adapter.list_tickets("queue")

        assert len(tickets) == 2
        assert all(isinstance(t, Ticket) for t in tickets)
        assert tickets[0].id == "42"
        assert tickets[0].title == "Test ticket"
        assert tickets[0].body == "Test body"
        assert tickets[0].labels == ["bug"]
        assert tickets[1].id == "43"

    def test_list_tickets_empty_column(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Returns empty list when column has no tickets."""
        mock_client.post.return_value = _mock_response(
            {
                "node": {
                    "items": {
                        "nodes": [
                            {
                                "id": "item_1",
                                "fieldValueByName": {"name": "In Progress"},
                                "content": {
                                    "number": 42,
                                    "title": "Test ticket",
                                    "body": "Test body",
                                    "labels": {"nodes": []},
                                },
                            },
                        ]
                    }
                }
            }
        )

        tickets = adapter.list_tickets("queue")

        assert tickets == []

    def test_list_tickets_filters_by_column(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Only returns tickets in the specified column."""
        mock_client.post.return_value = _mock_response(
            {
                "node": {
                    "items": {
                        "nodes": [
                            {
                                "id": "item_1",
                                "fieldValueByName": {"name": "Queue"},
                                "content": {
                                    "number": 1,
                                    "title": "Queue ticket",
                                    "body": "",
                                    "labels": {"nodes": []},
                                },
                            },
                            {
                                "id": "item_2",
                                "fieldValueByName": {"name": "In Progress"},
                                "content": {
                                    "number": 2,
                                    "title": "In progress ticket",
                                    "body": "",
                                    "labels": {"nodes": []},
                                },
                            },
                        ]
                    }
                }
            }
        )

        tickets = adapter.list_tickets("in_progress")

        assert len(tickets) == 1
        assert tickets[0].id == "2"
        assert tickets[0].title == "In progress ticket"


@pytest.mark.unit
class TestGetTicket:
    """Tests for get_ticket."""

    def test_get_ticket_returns_details(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Title, body, labels populated."""
        mock_client.post.return_value = _mock_response(
            {
                "repository": {
                    "issue": {
                        "number": 42,
                        "title": "Test ticket",
                        "body": "Test body content",
                        "labels": {"nodes": [{"name": "bug"}, {"name": "urgent"}]},
                    }
                }
            }
        )

        ticket = adapter.get_ticket("42")

        assert ticket.id == "42"
        assert ticket.title == "Test ticket"
        assert ticket.body == "Test body content"
        assert ticket.labels == ["bug", "urgent"]

    def test_get_ticket_not_found_raises(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Raises error for invalid ID."""
        mock_client.post.return_value = _mock_response({"repository": {"issue": None}})

        with pytest.raises(TicketNotFoundError) as exc_info:
            adapter.get_ticket("999")

        assert "999" in str(exc_info.value)


@pytest.mark.unit
class TestMoveTicket:
    """Tests for move_ticket."""

    def test_move_ticket_updates_column(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Ticket moved correctly."""
        # First call: get project items to find item ID
        # Second call: update the field value
        mock_client.post.side_effect = [
            _mock_response(
                {
                    "node": {
                        "items": {
                            "nodes": [
                                {"id": "PVTI_123", "content": {"number": 42}},
                            ]
                        }
                    }
                }
            ),
            _mock_response(
                {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "PVTI_123"}}}
            ),
        ]

        adapter.move_ticket("42", "in_progress")

        # Verify the mutation was called
        assert mock_client.post.call_count == 2
        # Check the second call (mutation) has correct variables
        mutation_call = mock_client.post.call_args_list[1]
        payload = (
            mutation_call.kwargs.get("json") or mutation_call.args[1]
            if len(mutation_call.args) > 1
            else mutation_call.kwargs["json"]
        )
        assert payload["variables"]["optionId"] == "opt_in_progress"

    def test_move_ticket_not_found_raises(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Raises error if ticket not in project."""
        mock_client.post.return_value = _mock_response({"node": {"items": {"nodes": []}}})

        with pytest.raises(TicketNotFoundError) as exc_info:
            adapter.move_ticket("999", "in_progress")

        assert "999" in str(exc_info.value)

    def test_move_ticket_invalid_column_raises(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Raises error for invalid column."""
        with pytest.raises(ColumnNotFoundError) as exc_info:
            adapter.move_ticket("42", "nonexistent_column")

        assert "nonexistent_column" in str(exc_info.value)


@pytest.mark.unit
class TestCloseTicket:
    """Tests for close_ticket."""

    def test_close_ticket_closes_issue(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Issue state set to closed."""
        # First call: get_ticket (verify exists)
        # Second call: get issue ID
        # Third call: close mutation
        mock_client.post.side_effect = [
            _mock_response(
                {
                    "repository": {
                        "issue": {
                            "number": 42,
                            "title": "Test",
                            "body": "",
                            "labels": {"nodes": []},
                        }
                    }
                }
            ),
            _mock_response({"repository": {"issue": {"id": "I_123"}}}),
            _mock_response({"closeIssue": {"issue": {"id": "I_123", "state": "CLOSED"}}}),
        ]

        adapter.close_ticket("42")

        # Verify the close mutation was called
        assert mock_client.post.call_count == 3

    def test_close_ticket_not_found_raises(
        self, adapter: KanbanAdapter, mock_client: MagicMock
    ) -> None:
        """Raises error if ticket doesn't exist."""
        mock_client.post.return_value = _mock_response({"repository": {"issue": None}})

        with pytest.raises(TicketNotFoundError) as exc_info:
            adapter.close_ticket("999")

        assert "999" in str(exc_info.value)
