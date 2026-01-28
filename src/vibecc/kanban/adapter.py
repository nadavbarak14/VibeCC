"""KanbanAdapter - Interfaces with GitHub Projects for ticket management."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from vibecc.kanban.exceptions import (
    ColumnNotFoundError,
    KanbanError,
    ProjectNotFoundError,
    TicketNotFoundError,
)
from vibecc.kanban.models import Ticket

logger = logging.getLogger("vibecc.kanban")

# Column name mapping from internal names to GitHub Project column names
COLUMNS = {
    "queue": "Todo",
    "todo": "Todo",
    "in_progress": "In Progress",
    "done": "Done",
    "failed": "Failed",
}


class KanbanAdapter:
    """Adapter for GitHub Projects (ProjectsV2) kanban board.

    Uses GitHub GraphQL API to interact with GitHub Projects.
    """

    def __init__(
        self,
        repo: str,
        project_number: int,
        token: str,
        base_url: str = "https://api.github.com/graphql",
    ) -> None:
        """Initialize Kanban Adapter.

        Args:
            repo: GitHub repo in "owner/repo" format
            project_number: GitHub Project number (visible in project URL)
            token: GitHub personal access token with project scope
            base_url: GitHub GraphQL API URL (for testing/enterprise)
        """
        self.repo = repo
        self.owner, self.repo_name = repo.split("/")
        self.project_number = project_number
        self.token = token
        self.base_url = base_url
        self._client: httpx.Client | None = None
        self._project_id: str | None = None
        self._status_field_id: str | None = None
        self._column_options: dict[str, str] | None = None  # name -> option_id

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client for GraphQL API."""
        if self._client is None:
            self._client = httpx.Client(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data

        Raises:
            KanbanError: If query fails
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        response = self.client.post(self.base_url, json=payload)

        if response.status_code != 200:
            raise KanbanError(f"GraphQL request failed: {response.status_code} - {response.text}")

        data: dict[str, Any] = response.json()
        if "errors" in data:
            raise KanbanError(f"GraphQL errors: {data['errors']}")

        return dict(data["data"])

    def _ensure_project_metadata(self) -> None:
        """Fetch and cache project metadata (ID, status field, column options)."""
        if self._project_id is not None:
            return

        # Try user-level project first (most common for personal projects)
        project = self._try_fetch_user_project()
        if not project:
            # Fall back to repository-level project
            project = self._try_fetch_repo_project()

        if not project:
            raise ProjectNotFoundError(
                f"Project #{self.project_number} not found for "
                f"user {self.owner} or repo {self.repo}"
            )

        self._project_id = project["id"]

        status_field = project.get("field")
        if not status_field:
            raise KanbanError("Status field not found in project")

        self._status_field_id = status_field["id"]
        self._column_options = {opt["name"]: opt["id"] for opt in status_field["options"]}

    def _try_fetch_user_project(self) -> dict[str, Any] | None:
        """Try to fetch project from user level."""
        query = """
        query($owner: String!, $projectNumber: Int!) {
            user(login: $owner) {
                projectV2(number: $projectNumber) {
                    id
                    field(name: "Status") {
                        ... on ProjectV2SingleSelectField {
                            id
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            data = self._graphql(
                query,
                {"owner": self.owner, "projectNumber": self.project_number},
            )
            result: dict[str, Any] | None = data.get("user", {}).get("projectV2")
            return result
        except KanbanError:
            return None

    def _try_fetch_repo_project(self) -> dict[str, Any] | None:
        """Try to fetch project from repository level."""
        query = """
        query($owner: String!, $repo: String!, $projectNumber: Int!) {
            repository(owner: $owner, name: $repo) {
                projectV2(number: $projectNumber) {
                    id
                    field(name: "Status") {
                        ... on ProjectV2SingleSelectField {
                            id
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        try:
            data = self._graphql(
                query,
                {
                    "owner": self.owner,
                    "repo": self.repo_name,
                    "projectNumber": self.project_number,
                },
            )
            result: dict[str, Any] | None = data.get("repository", {}).get("projectV2")
            return result
        except KanbanError:
            return None

    def _get_column_option_id(self, column: str) -> str:
        """Get the GitHub option ID for a column name.

        Args:
            column: Internal column name (e.g., "queue", "in_progress")

        Returns:
            GitHub option ID for the column

        Raises:
            ColumnNotFoundError: If column doesn't exist
        """
        self._ensure_project_metadata()

        # Map internal name to GitHub column name
        github_column = COLUMNS.get(column, column)

        if self._column_options is None:
            raise KanbanError("Column options not loaded")

        option_id = self._column_options.get(github_column)
        if not option_id:
            raise ColumnNotFoundError(
                f"Column '{column}' (GitHub: '{github_column}') not found. "
                f"Available: {list(self._column_options.keys())}"
            )

        return option_id

    def list_tickets(self, column: str) -> list[Ticket]:
        """Get all tickets in a column.

        Args:
            column: Column name (e.g., "queue", "in_progress")

        Returns:
            List of Ticket objects in the column
        """
        logger.debug("Listing tickets in column: %s", column)
        self._ensure_project_metadata()
        github_column = COLUMNS.get(column, column)

        # Query to get all items in the project with their status
        query = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: 100) {
                        nodes {
                            id
                            fieldValueByName(name: "Status") {
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    name
                                }
                            }
                            content {
                                ... on Issue {
                                    number
                                    title
                                    body
                                    labels(first: 10) {
                                        nodes {
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        data = self._graphql(query, {"projectId": self._project_id})

        items = data.get("node", {}).get("items", {}).get("nodes", [])
        tickets = []

        for item in items:
            # Check if item is in the requested column
            status_value = item.get("fieldValueByName")
            if not status_value:
                continue
            if status_value.get("name") != github_column:
                continue

            content = item.get("content")
            if not content:
                continue

            # Extract labels
            label_nodes = content.get("labels", {}).get("nodes", [])
            labels = [label["name"] for label in label_nodes]

            tickets.append(
                Ticket(
                    id=str(content["number"]),
                    title=content["title"],
                    body=content.get("body") or "",
                    labels=labels,
                )
            )

        logger.info("Found %d ticket(s) in column %s", len(tickets), column)
        return tickets

    def get_ticket(self, ticket_id: str) -> Ticket:
        """Get ticket details by issue number.

        Args:
            ticket_id: GitHub issue number

        Returns:
            Ticket object with details

        Raises:
            TicketNotFoundError: If ticket doesn't exist
        """
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                    number
                    title
                    body
                    labels(first: 10) {
                        nodes {
                            name
                        }
                    }
                }
            }
        }
        """

        data = self._graphql(
            query,
            {
                "owner": self.owner,
                "repo": self.repo_name,
                "number": int(ticket_id),
            },
        )

        issue = data.get("repository", {}).get("issue")
        if not issue:
            raise TicketNotFoundError(f"Ticket #{ticket_id} not found in {self.repo}")

        label_nodes = issue.get("labels", {}).get("nodes", [])
        labels = [label["name"] for label in label_nodes]

        return Ticket(
            id=str(issue["number"]),
            title=issue["title"],
            body=issue.get("body") or "",
            labels=labels,
        )

    def move_ticket(self, ticket_id: str, column: str) -> None:
        """Move a ticket to a different column.

        Args:
            ticket_id: GitHub issue number
            column: Target column name (e.g., "queue", "in_progress")

        Raises:
            TicketNotFoundError: If ticket not in project
            ColumnNotFoundError: If column doesn't exist
        """
        logger.info("Moving ticket #%s to column: %s", ticket_id, column)
        self._ensure_project_metadata()
        option_id = self._get_column_option_id(column)

        # First, find the project item ID for this issue
        item_id = self._get_project_item_id(ticket_id)

        # Update the status field
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
            updateProjectV2ItemFieldValue(
                input: {
                    projectId: $projectId
                    itemId: $itemId
                    fieldId: $fieldId
                    value: { singleSelectOptionId: $optionId }
                }
            ) {
                projectV2Item {
                    id
                }
            }
        }
        """

        self._graphql(
            mutation,
            {
                "projectId": self._project_id,
                "itemId": item_id,
                "fieldId": self._status_field_id,
                "optionId": option_id,
            },
        )
        logger.info("Moved ticket #%s to %s", ticket_id, column)

    def _get_project_item_id(self, ticket_id: str) -> str:
        """Get the project item ID for an issue.

        Args:
            ticket_id: GitHub issue number

        Returns:
            Project item ID

        Raises:
            TicketNotFoundError: If ticket not in project
        """
        self._ensure_project_metadata()

        query = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: 100) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    number
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        data = self._graphql(query, {"projectId": self._project_id})

        items = data.get("node", {}).get("items", {}).get("nodes", [])
        for item in items:
            content = item.get("content")
            if content and str(content.get("number")) == ticket_id:
                return str(item["id"])

        raise TicketNotFoundError(f"Ticket #{ticket_id} not found in project")

    def close_ticket(self, ticket_id: str) -> None:
        """Close a ticket (GitHub issue).

        Args:
            ticket_id: GitHub issue number

        Raises:
            TicketNotFoundError: If ticket doesn't exist
        """
        logger.info("Closing ticket #%s", ticket_id)
        # First verify the ticket exists
        self.get_ticket(ticket_id)

        # We need to get the issue node ID first
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                    id
                }
            }
        }
        """

        data = self._graphql(
            query,
            {
                "owner": self.owner,
                "repo": self.repo_name,
                "number": int(ticket_id),
            },
        )

        issue_id = data.get("repository", {}).get("issue", {}).get("id")
        if not issue_id:
            raise TicketNotFoundError(f"Ticket #{ticket_id} not found")

        close_mutation = """
        mutation($issueId: ID!) {
            closeIssue(input: { issueId: $issueId }) {
                issue {
                    id
                    state
                }
            }
        }
        """

        self._graphql(close_mutation, {"issueId": issue_id})
        logger.info("Closed ticket #%s", ticket_id)
