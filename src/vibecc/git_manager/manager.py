"""GitManager - Handles git and GitHub operations for the pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path

import httpx

from vibecc.git_manager.exceptions import (
    BranchError,
    MergeError,
    PRError,
    PushError,
)
from vibecc.git_manager.models import PR, CIStatus


class GitManager:
    """Manages git and GitHub operations for the pipeline.

    Handles branch creation, pushing, PR management, and merging.
    Assumes the repository is already cloned locally.
    """

    def __init__(
        self,
        repo: str,
        token: str,
        repo_path: str | Path = ".",
        base_url: str = "https://api.github.com",
    ) -> None:
        """Initialize Git Manager.

        Args:
            repo: GitHub repo in "owner/repo" format
            token: GitHub personal access token
            repo_path: Path to local repository clone
            base_url: GitHub API base URL (for testing/enterprise)
        """
        self.repo = repo
        self.token = token
        self.repo_path = Path(repo_path)
        self.base_url = base_url.rstrip("/")
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client for GitHub API."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=30.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _run_git(self, *args: str) -> str:
        """Run a git command in the repo directory.

        Args:
            *args: Git command arguments

        Returns:
            Command stdout

        Raises:
            subprocess.CalledProcessError: If command fails
        """
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def create_branch(self, ticket_id: str, base: str = "main") -> str:
        """Create a new branch for a ticket.

        Creates branch named `ticket-{ticket_id}` from the specified base branch.

        Args:
            ticket_id: The ticket/issue ID
            base: Base branch to create from (default: main)

        Returns:
            The created branch name

        Raises:
            BranchError: If branch creation fails
        """
        branch_name = f"ticket-{ticket_id}"
        try:
            # Fetch latest from origin
            self._run_git("fetch", "origin", base)
            # Create and checkout the new branch from origin/base
            self._run_git("checkout", "-b", branch_name, f"origin/{base}")
        except subprocess.CalledProcessError as e:
            raise BranchError(
                f"Failed to create branch '{branch_name}' from '{base}': {e.stderr}"
            ) from e
        return branch_name

    def push(self, branch: str) -> None:
        """Push a branch to origin.

        Args:
            branch: Branch name to push

        Raises:
            PushError: If push fails
        """
        try:
            self._run_git("push", "-u", "origin", branch)
        except subprocess.CalledProcessError as e:
            raise PushError(f"Failed to push branch '{branch}': {e.stderr}") from e

    def create_pr(self, branch: str, title: str, body: str, base: str = "main") -> PR:
        """Create a pull request.

        Args:
            branch: Head branch (the branch with changes)
            title: PR title
            body: PR description
            base: Base branch to merge into (default: main)

        Returns:
            PR object with id, url, and number

        Raises:
            PRError: If PR creation fails
        """
        response = self.client.post(
            f"/repos/{self.repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": base,
            },
        )

        if response.status_code != 201:
            raise PRError(f"Failed to create PR: {response.status_code} - {response.text}")

        data = response.json()
        return PR(
            id=data["id"],
            url=data["html_url"],
            number=data["number"],
        )

    def get_pr_ci_status(self, pr_number: int) -> CIStatus:
        """Get the CI status for a pull request.

        Checks the combined status of all checks on the PR's head commit.

        Args:
            pr_number: The PR number

        Returns:
            CIStatus indicating pending, success, or failure

        Raises:
            PRError: If status check fails
        """
        # First, get the PR to find the head SHA
        pr_response = self.client.get(f"/repos/{self.repo}/pulls/{pr_number}")
        if pr_response.status_code != 200:
            raise PRError(
                f"Failed to get PR {pr_number}: {pr_response.status_code} - {pr_response.text}"
            )

        pr_data = pr_response.json()
        head_sha = pr_data["head"]["sha"]

        # Get the combined status for the commit
        status_response = self.client.get(f"/repos/{self.repo}/commits/{head_sha}/status")
        if status_response.status_code != 200:
            raise PRError(
                f"Failed to get status: {status_response.status_code} - {status_response.text}"
            )

        status_data = status_response.json()
        state = status_data["state"]

        # Also check GitHub Actions check runs
        checks_response = self.client.get(f"/repos/{self.repo}/commits/{head_sha}/check-runs")

        if checks_response.status_code == 200:
            checks_data = checks_response.json()
            check_runs = checks_data.get("check_runs", [])

            if check_runs:
                # If any check is in progress or queued, status is pending
                for check in check_runs:
                    if check["status"] != "completed":
                        return CIStatus.PENDING
                    if check["conclusion"] not in ("success", "skipped", "neutral"):
                        return CIStatus.FAILURE

                # All checks completed successfully
                if state == "pending" and all(
                    c["conclusion"] in ("success", "skipped", "neutral") for c in check_runs
                ):
                    return CIStatus.SUCCESS

        # Map GitHub status to CIStatus
        if state == "success":
            return CIStatus.SUCCESS
        elif state == "pending":
            return CIStatus.PENDING
        else:  # failure, error
            return CIStatus.FAILURE

    def merge_pr(self, pr_number: int) -> None:
        """Merge a pull request using rebase strategy.

        Args:
            pr_number: The PR number to merge

        Raises:
            MergeError: If merge fails
        """
        response = self.client.put(
            f"/repos/{self.repo}/pulls/{pr_number}/merge",
            json={
                "merge_method": "rebase",
            },
        )

        if response.status_code != 200:
            raise MergeError(
                f"Failed to merge PR {pr_number}: {response.status_code} - {response.text}"
            )

    def delete_branch(self, branch: str) -> None:
        """Delete a remote branch.

        Args:
            branch: Branch name to delete

        Raises:
            BranchError: If deletion fails
        """
        response = self.client.delete(f"/repos/{self.repo}/git/refs/heads/{branch}")

        # 204 = success, 422 = branch already deleted
        if response.status_code not in (204, 422):
            raise BranchError(
                f"Failed to delete branch '{branch}': {response.status_code} - {response.text}"
            )
