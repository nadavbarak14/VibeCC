"""Testing Runner - Push, create PR, and wait for CI."""

from __future__ import annotations

import logging
import time

from vibecc.git_manager import CIStatus, GitManager
from vibecc.workers.models import TestingResult, TestingTask

logger = logging.getLogger("vibecc.workers.testing")


class TestingRunner:
    """Worker that pushes code, creates a PR, and waits for CI to pass.

    Handles the testing phase of the pipeline by pushing the branch,
    creating a pull request, and polling CI status until completion.
    """

    def __init__(
        self,
        git_manager: GitManager,
        poll_interval: int = 30,
        max_polls: int | None = None,
    ) -> None:
        """Initialize the Testing Runner.

        Args:
            git_manager: GitManager instance for git/GitHub operations.
            poll_interval: Seconds between CI status checks (default: 30).
            max_polls: Maximum number of polls before giving up (None = unlimited).
        """
        self.git_manager = git_manager
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    def execute(self, task: TestingTask) -> TestingResult:
        """Execute a testing task.

        Pushes the branch, creates a PR, and polls CI until complete.

        Args:
            task: The testing task to execute.

        Returns:
            TestingResult with PR info and CI status.
        """
        logger.info("Executing testing task for ticket #%s: %s", task.ticket_id, task.ticket_title)

        # Push branch to origin
        self.git_manager.push(task.branch)

        # Create PR with ticket info
        pr = self.git_manager.create_pr(
            branch=task.branch,
            title=f"#{task.ticket_id}: {task.ticket_title}",
            body=f"Closes #{task.ticket_id}",
        )
        logger.info("Created PR #%d: %s", pr.number, pr.url)

        # Poll CI status until complete
        logger.info("Polling CI status (interval=%ds)...", self.poll_interval)
        ci_status = self._poll_ci_status(pr.number)
        logger.info("CI completed with status: %s", ci_status.value)

        # On failure, fetch logs
        failure_logs = None
        if ci_status == CIStatus.FAILURE:
            logger.info("Fetching CI failure logs...")
            failure_logs = self._fetch_failure_logs(pr.number)
            logger.debug("Failure logs: %s", failure_logs[:500] if failure_logs else "(none)")

        result = TestingResult(
            success=ci_status == CIStatus.SUCCESS,
            pr_id=pr.id,
            pr_url=pr.url,
            ci_status=ci_status,
            failure_logs=failure_logs,
        )
        logger.info("Testing task completed: success=%s", result.success)
        return result

    def _poll_ci_status(self, pr_number: int) -> CIStatus:
        """Poll CI status until complete or max polls reached.

        Args:
            pr_number: The PR number to check.

        Returns:
            Final CIStatus (SUCCESS or FAILURE).
        """
        polls = 0
        while True:
            status = self.git_manager.get_pr_ci_status(pr_number)
            logger.debug("Poll %d: CI status = %s", polls + 1, status.value)

            if status != CIStatus.PENDING:
                return status

            polls += 1
            if self.max_polls is not None and polls >= self.max_polls:
                logger.warning("Max polls (%d) reached, treating as failure", self.max_polls)
                return CIStatus.FAILURE

            logger.debug("CI pending, waiting %ds before next poll...", self.poll_interval)
            time.sleep(self.poll_interval)

    def _fetch_failure_logs(self, pr_number: int) -> str:
        """Fetch CI failure logs for a PR.

        Args:
            pr_number: The PR number to fetch logs for.

        Returns:
            Failure logs/summary string.
        """
        # Get the PR head SHA
        pr_response = self.git_manager.client.get(
            f"/repos/{self.git_manager.repo}/pulls/{pr_number}"
        )
        if pr_response.status_code != 200:
            return "Failed to fetch PR details"

        pr_data = pr_response.json()
        head_sha = pr_data["head"]["sha"]

        # Get check runs to find failed checks
        checks_response = self.git_manager.client.get(
            f"/repos/{self.git_manager.repo}/commits/{head_sha}/check-runs"
        )
        if checks_response.status_code != 200:
            return "Failed to fetch check runs"

        checks_data = checks_response.json()
        check_runs = checks_data.get("check_runs", [])

        # Collect failure info from each failed check
        failures = []
        for check in check_runs:
            if check.get("conclusion") not in ("success", "skipped", "neutral", None):
                name = check.get("name", "Unknown")
                conclusion = check.get("conclusion", "unknown")
                output = check.get("output", {})
                title = output.get("title", "")
                summary = output.get("summary", "")

                failure_info = f"Check '{name}' failed with conclusion: {conclusion}"
                if title:
                    failure_info += f"\nTitle: {title}"
                if summary:
                    failure_info += f"\nSummary: {summary}"

                failures.append(failure_info)

        if failures:
            return "\n\n".join(failures)

        return "CI failed but no specific failure logs found"
