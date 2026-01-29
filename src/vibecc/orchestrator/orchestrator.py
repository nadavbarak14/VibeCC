"""Orchestrator - Pipeline state machine management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from vibecc.orchestrator.exceptions import PipelineProcessingError
from vibecc.orchestrator.models import AutopilotStatus
from vibecc.state_store import PipelineState, StateStore
from vibecc.workers import CodingTask, TestingTask

if TYPE_CHECKING:
    from vibecc.api.events import EventManager
    from vibecc.git_manager import GitManager
    from vibecc.kanban import KanbanAdapter, Ticket
    from vibecc.state_store import Pipeline, Project
    from vibecc.workers import CoderWorker, TestingRunner

logger = logging.getLogger(__name__)


class Orchestrator:
    """Manages pipeline state transitions and coordinates workers.

    The Orchestrator is the brain of the VibeCC system. It:
    - Tracks autopilot status per project
    - Creates pipelines from tickets
    - Drives pipelines through state transitions
    - Coordinates workers (Coder, Testing)
    - Emits events for dashboard updates
    - Handles retries and failure scenarios
    """

    def __init__(
        self,
        state_store: StateStore,
        event_manager: EventManager,
    ) -> None:
        """Initialize the Orchestrator.

        Args:
            state_store: StateStore instance for pipeline persistence.
            event_manager: EventManager instance for emitting events.
        """
        self.state_store = state_store
        self.event_manager = event_manager
        self._autopilot_running: dict[str, bool] = {}

    def get_autopilot_status(self, project_id: str) -> AutopilotStatus:
        """Get autopilot status for a project.

        Args:
            project_id: The project's unique ID.

        Returns:
            AutopilotStatus with current state information.
        """
        project = self.state_store.get_project(project_id)

        # Count active pipelines (in-progress states)
        active_states = [
            PipelineState.CODING,
            PipelineState.TESTING,
            PipelineState.REVIEW,
        ]
        active_pipelines = 0
        for state in active_states:
            pipelines = self.state_store.list_pipelines(project_id=project_id, state=state)
            active_pipelines += len(pipelines)

        # Count queued pipelines
        queued_pipelines = self.state_store.list_pipelines(
            project_id=project_id, state=PipelineState.QUEUED
        )
        queued_tickets = len(queued_pipelines)

        return AutopilotStatus(
            project_id=project.id,
            running=self._autopilot_running.get(project_id, False),
            active_pipelines=active_pipelines,
            queued_tickets=queued_tickets,
        )

    def start_autopilot(self, project_id: str) -> None:
        """Start autopilot for a project.

        Args:
            project_id: The project's unique ID.
        """
        # Verify project exists
        self.state_store.get_project(project_id)

        self._autopilot_running[project_id] = True
        logger.info("Autopilot started for project %s", project_id)
        self.event_manager.emit_autopilot_started(project_id)

    def stop_autopilot(self, project_id: str, reason: str = "manual") -> None:
        """Stop autopilot for a project.

        Args:
            project_id: The project's unique ID.
            reason: Reason for stopping (e.g., "manual", "max_retries").
        """
        self._autopilot_running[project_id] = False
        logger.info("Autopilot stopped for project %s: %s", project_id, reason)
        self.event_manager.emit_autopilot_stopped(project_id, reason)

    def start_pipeline(
        self,
        project_id: str,
        ticket: Ticket,
        git_manager: GitManager,
    ) -> Pipeline:
        """Start a new pipeline for a ticket.

        Creates a branch and pipeline record, then transitions to CODING state.

        Args:
            project_id: The project's unique ID.
            ticket: The ticket to process.
            git_manager: GitManager for branch creation.

        Returns:
            The created Pipeline object.
        """
        project = self.state_store.get_project(project_id)

        # Create branch
        logger.info("Creating branch for ticket #%s", ticket.id)
        branch_name = git_manager.create_branch(ticket.id, project.base_branch)
        logger.info("Created branch %s", branch_name)

        # Create pipeline record
        pipeline = self.state_store.create_pipeline(
            project_id=project_id,
            ticket_id=ticket.id,
            ticket_title=ticket.title,
            branch_name=branch_name,
            ticket_body=ticket.body,
        )

        logger.info("Created pipeline %s for ticket #%s", pipeline.id, ticket.id)

        # Emit event
        self.event_manager.emit_pipeline_created(
            pipeline_id=pipeline.id,
            project_id=project_id,
            ticket_id=ticket.id,
            state=pipeline.state,
        )

        self._log_pipeline(pipeline, "info", f"Pipeline created in state {pipeline.state}")

        return pipeline

    def process_pipeline(
        self,
        pipeline_id: str,
        git_manager: GitManager,
        kanban: KanbanAdapter,
        coder_worker: CoderWorker,
        testing_runner: TestingRunner,
        repo_path: str,
    ) -> None:
        """Process a pipeline through its current state.

        This method handles one state transition at a time. Call repeatedly
        until pipeline reaches a terminal state (MERGED or FAILED).

        Args:
            pipeline_id: The pipeline's unique ID.
            git_manager: GitManager for git operations.
            kanban: KanbanAdapter for ticket management.
            coder_worker: CoderWorker for coding tasks.
            testing_runner: TestingRunner for testing tasks.
            repo_path: Path to the git repository.

        Raises:
            PipelineProcessingError: If processing fails unexpectedly.
        """
        pipeline = self.state_store.get_pipeline(pipeline_id)
        project = self.state_store.get_project(pipeline.project_id)

        logger.info(
            "Processing pipeline %s in state %s",
            pipeline_id,
            pipeline.state,
        )

        try:
            match pipeline.pipeline_state:
                case PipelineState.QUEUED:
                    self._process_queued(pipeline, project)
                case PipelineState.CODING:
                    self._process_coding(pipeline, project, coder_worker, repo_path)
                case PipelineState.TESTING:
                    self._process_testing(
                        pipeline, project, git_manager, kanban, testing_runner, repo_path
                    )
                case PipelineState.MERGED:
                    logger.info("Pipeline %s already merged", pipeline_id)
                case PipelineState.FAILED:
                    logger.info("Pipeline %s already failed", pipeline_id)
                case _:
                    raise PipelineProcessingError(f"Unknown pipeline state: {pipeline.state}")
        except Exception as e:
            logger.exception("Error processing pipeline %s: %s", pipeline_id, e)
            self._log_pipeline(pipeline, "error", f"Processing error: {e}")
            raise PipelineProcessingError(f"Failed to process pipeline: {e}") from e

    def get_status(self, pipeline_id: str) -> Pipeline:
        """Get current pipeline status.

        Args:
            pipeline_id: The pipeline's unique ID.

        Returns:
            The Pipeline object with current state.
        """
        return self.state_store.get_pipeline(pipeline_id)

    def _process_queued(self, pipeline: Pipeline, project: Project) -> None:
        """Process a pipeline in QUEUED state.

        Transitions directly to CODING since branch is already created.
        """
        previous_state = pipeline.state

        # Move to CODING
        self.state_store.update_pipeline(
            pipeline.id,
            state=PipelineState.CODING,
        )

        logger.info(
            "Pipeline %s transitioned from %s to %s",
            pipeline.id,
            previous_state,
            PipelineState.CODING.value,
        )

        self.event_manager.emit_pipeline_updated(
            pipeline_id=pipeline.id,
            project_id=project.id,
            state=PipelineState.CODING.value,
            previous_state=previous_state,
        )

        self._log_pipeline(pipeline, "info", "Transitioned to CODING state")

    def _process_coding(
        self,
        pipeline: Pipeline,
        project: Project,
        coder_worker: CoderWorker,
        repo_path: str,
    ) -> None:
        """Process a pipeline in CODING state.

        Runs the CoderWorker and transitions based on result.
        """
        self._log_pipeline(pipeline, "info", "Starting coding phase")

        # Build coding task
        task = CodingTask(
            ticket_id=pipeline.ticket_id,
            ticket_title=pipeline.ticket_title,
            ticket_body=pipeline.ticket_body,
            repo_path=repo_path,
            branch=pipeline.branch_name,
            feedback=pipeline.feedback,
        )

        # Execute coding task
        result = coder_worker.execute(task)

        if result.success:
            self._log_pipeline(pipeline, "info", "Coding completed successfully")

            # Transition to TESTING
            previous_state = pipeline.state
            self.state_store.update_pipeline(
                pipeline.id,
                state=PipelineState.TESTING,
                feedback=None,  # Clear feedback on success
            )

            logger.info("Pipeline %s transitioned to TESTING", pipeline.id)

            self.event_manager.emit_pipeline_updated(
                pipeline_id=pipeline.id,
                project_id=project.id,
                state=PipelineState.TESTING.value,
                previous_state=previous_state,
            )

            self._log_pipeline(pipeline, "info", "Transitioned to TESTING state")
        else:
            self._handle_coding_failure(pipeline, project, result.error or "Unknown error")

    def _handle_coding_failure(
        self,
        pipeline: Pipeline,
        project: Project,
        error: str,
    ) -> None:
        """Handle a coding failure.

        For phase 1, coding failures go directly to FAILED state.
        """
        self._log_pipeline(pipeline, "error", f"Coding failed: {error}")

        # Move to FAILED
        previous_state = pipeline.state
        self.state_store.update_pipeline(
            pipeline.id,
            state=PipelineState.FAILED,
            feedback=error,
        )

        logger.info("Pipeline %s transitioned to FAILED", pipeline.id)

        self.event_manager.emit_pipeline_updated(
            pipeline_id=pipeline.id,
            project_id=project.id,
            state=PipelineState.FAILED.value,
            previous_state=previous_state,
        )

        self.event_manager.emit_pipeline_completed(
            pipeline_id=pipeline.id,
            project_id=project.id,
            final_state=PipelineState.FAILED.value,
        )

        # Save to history
        updated_pipeline = self.state_store.get_pipeline(pipeline.id)
        self.state_store.save_to_history(updated_pipeline)

        self._log_pipeline(pipeline, "info", "Pipeline completed with FAILED state")

        # Stop autopilot for project
        self.stop_autopilot(project.id, reason="coding_failure")

    def _process_testing(
        self,
        pipeline: Pipeline,
        project: Project,
        git_manager: GitManager,
        kanban: KanbanAdapter,
        testing_runner: TestingRunner,
        repo_path: str,
    ) -> None:
        """Process a pipeline in TESTING state.

        Runs the TestingRunner and handles CI results.
        """
        self._log_pipeline(pipeline, "info", "Starting testing phase")

        # Build testing task
        task = TestingTask(
            ticket_id=pipeline.ticket_id,
            ticket_title=pipeline.ticket_title,
            branch=pipeline.branch_name,
            repo_path=repo_path,
        )

        # Execute testing task
        result = testing_runner.execute(task)

        # Update PR info
        self.state_store.update_pipeline(
            pipeline.id,
            pr_id=result.pr_id,
            pr_url=result.pr_url,
        )

        if result.success:
            self._handle_testing_success(pipeline, project, git_manager, kanban)
        else:
            self._handle_testing_failure(pipeline, project, result.failure_logs or "CI failed")

    def _handle_testing_success(
        self,
        pipeline: Pipeline,
        project: Project,
        git_manager: GitManager,
        kanban: KanbanAdapter,
    ) -> None:
        """Handle successful CI.

        Merges PR, deletes branch, closes ticket, and completes pipeline.
        """
        self._log_pipeline(pipeline, "info", "CI passed, merging PR")

        # Refresh pipeline to get PR info
        pipeline = self.state_store.get_pipeline(pipeline.id)

        if pipeline.pr_id:
            # Merge PR
            git_manager.merge_pr(pipeline.pr_id)
            self._log_pipeline(pipeline, "info", f"Merged PR #{pipeline.pr_id}")

            # Delete branch
            git_manager.delete_branch(pipeline.branch_name)
            self._log_pipeline(pipeline, "info", f"Deleted branch {pipeline.branch_name}")

        # Close ticket
        kanban.close_ticket(pipeline.ticket_id)
        self._log_pipeline(pipeline, "info", f"Closed ticket #{pipeline.ticket_id}")

        # Move ticket to done column
        try:
            kanban.move_ticket(pipeline.ticket_id, "done")
        except Exception as e:
            # Non-fatal - ticket may not be in project
            logger.warning("Failed to move ticket to done: %s", e)

        # Transition to MERGED
        previous_state = pipeline.state
        self.state_store.update_pipeline(
            pipeline.id,
            state=PipelineState.MERGED,
        )

        logger.info("Pipeline %s transitioned to MERGED", pipeline.id)

        self.event_manager.emit_pipeline_updated(
            pipeline_id=pipeline.id,
            project_id=project.id,
            state=PipelineState.MERGED.value,
            previous_state=previous_state,
        )

        self.event_manager.emit_pipeline_completed(
            pipeline_id=pipeline.id,
            project_id=project.id,
            final_state=PipelineState.MERGED.value,
        )

        # Save to history
        updated_pipeline = self.state_store.get_pipeline(pipeline.id)
        self.state_store.save_to_history(updated_pipeline)

        self._log_pipeline(pipeline, "info", "Pipeline completed with MERGED state")

    def _handle_testing_failure(
        self,
        pipeline: Pipeline,
        project: Project,
        failure_logs: str,
    ) -> None:
        """Handle CI failure.

        Checks retry count and either retries (back to CODING) or fails.
        """
        self._log_pipeline(pipeline, "warning", f"CI failed: {failure_logs[:200]}...")

        new_retry_count = pipeline.retry_count_ci + 1

        if new_retry_count >= project.max_retries_ci:
            # Max retries exceeded - move to FAILED
            self._log_pipeline(
                pipeline,
                "error",
                f"Max CI retries ({project.max_retries_ci}) exceeded",
            )

            previous_state = pipeline.state
            self.state_store.update_pipeline(
                pipeline.id,
                state=PipelineState.FAILED,
                retry_count_ci=new_retry_count,
                feedback=failure_logs,
            )

            logger.info("Pipeline %s transitioned to FAILED (max retries)", pipeline.id)

            self.event_manager.emit_pipeline_updated(
                pipeline_id=pipeline.id,
                project_id=project.id,
                state=PipelineState.FAILED.value,
                previous_state=previous_state,
            )

            self.event_manager.emit_pipeline_completed(
                pipeline_id=pipeline.id,
                project_id=project.id,
                final_state=PipelineState.FAILED.value,
            )

            # Save to history
            updated_pipeline = self.state_store.get_pipeline(pipeline.id)
            self.state_store.save_to_history(updated_pipeline)

            self._log_pipeline(pipeline, "info", "Pipeline completed with FAILED state")

            # Stop autopilot for project
            self.stop_autopilot(project.id, reason="max_retries")
        else:
            # Retry - go back to CODING with feedback
            self._log_pipeline(
                pipeline,
                "info",
                f"Retrying (attempt {new_retry_count + 1}/{project.max_retries_ci})",
            )

            previous_state = pipeline.state
            self.state_store.update_pipeline(
                pipeline.id,
                state=PipelineState.CODING,
                retry_count_ci=new_retry_count,
                feedback=failure_logs,
            )

            logger.info(
                "Pipeline %s back to CODING for retry %d",
                pipeline.id,
                new_retry_count,
            )

            self.event_manager.emit_pipeline_updated(
                pipeline_id=pipeline.id,
                project_id=project.id,
                state=PipelineState.CODING.value,
                previous_state=previous_state,
            )

            self._log_pipeline(
                pipeline,
                "info",
                "Transitioned back to CODING state with CI feedback",
            )

    def _log_pipeline(self, pipeline: Pipeline, level: str, message: str) -> None:
        """Emit a log event for a pipeline.

        Args:
            pipeline: The pipeline to log for.
            level: Log level (info, warning, error).
            message: Log message.
        """
        self.event_manager.emit_log(
            pipeline_id=pipeline.id,
            project_id=pipeline.project_id,
            level=level,
            message=message,
        )
