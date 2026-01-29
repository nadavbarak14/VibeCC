"""Background worker for processing pipelines."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import traceback
from typing import TYPE_CHECKING

from vibecc.git_manager import GitManager
from vibecc.kanban import KanbanAdapter
from vibecc.state_store import PipelineState
from vibecc.workers import CoderWorker, TestingRunner

if TYPE_CHECKING:
    from vibecc.orchestrator import Orchestrator
    from vibecc.state_store import StateStore

logger = logging.getLogger(__name__)

# Track running worker threads per project
_worker_tasks: dict[str, threading.Thread] = {}


def _get_github_token() -> str:
    """Get GitHub token from environment or gh CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def start_worker_sync(  # noqa: PLR0912, PLR0915
    project_id: str,
    state_store: StateStore,
    orchestrator: Orchestrator,
    repo_path: str = ".",
    max_concurrent: int = 1,
) -> None:
    """Synchronous worker that processes pipelines.

    This runs in a thread via BackgroundTasks.
    """
    print(f"[WORKER] Started for project {project_id}", flush=True)
    logger.info("Worker started for project %s", project_id)

    try:
        token = _get_github_token()
        print(f"[WORKER] Got token: {'yes' if token else 'NO'}", flush=True)
        if not token:
            print("[WORKER] ERROR: No GitHub token available", flush=True)
            orchestrator.stop_autopilot(project_id, reason="no_github_token")
            return

        project = state_store.get_project(project_id)
        print(f"[WORKER] Got project: {project.name}", flush=True)
        if not project.github_project_id:
            print("[WORKER] ERROR: Project has no github_project_id", flush=True)
            orchestrator.stop_autopilot(project_id, reason="no_github_project")
            return

        print(f"[WORKER] Project: {project.name}, repo: {project.repo}", flush=True)
    except Exception as e:
        print(f"[WORKER] INIT ERROR: {e}", flush=True)
        traceback.print_exc()
        return

    # Create workers
    coder_worker = CoderWorker()

    try:
        while orchestrator._autopilot_running.get(project_id, False):
            # Count working pipelines (CODING, TESTING, REVIEW)
            working_states = [
                PipelineState.CODING,
                PipelineState.TESTING,
                PipelineState.REVIEW,
            ]
            working_pipelines = []
            for state in working_states:
                working_pipelines.extend(
                    state_store.list_pipelines(project_id=project_id, state=state)
                )

            # Get queued pipelines
            queued_pipelines = state_store.list_pipelines(
                project_id=project_id, state=PipelineState.QUEUED
            )

            working_count = len(working_pipelines)
            queued_count = len(queued_pipelines)

            print(f"[WORKER] working={working_count}, queued={queued_count}", flush=True)

            # If we have working pipelines, process them first
            if working_pipelines:
                pipeline = working_pipelines[0]
                state_val = pipeline.pipeline_state.value
                print(
                    f"[WORKER] Processing working pipeline #{pipeline.ticket_id} ({state_val})",
                    flush=True,
                )
            # Otherwise, if we have capacity, start a queued pipeline
            elif queued_count > 0 and working_count < max_concurrent:
                pipeline = queued_pipelines[0]
                print(f"[WORKER] Starting queued pipeline #{pipeline.ticket_id}", flush=True)
            else:
                # Nothing to do - either no pipelines or at capacity
                if queued_count > 0:
                    msg = f"[WORKER] At capacity ({working_count}/{max_concurrent}), waiting..."
                    print(msg, flush=True)
                else:
                    print("[WORKER] No pipelines to process, waiting...", flush=True)
                time.sleep(2)
                continue

            # Check if still running
            if not orchestrator._autopilot_running.get(project_id, False):
                break

            state_val = pipeline.pipeline_state.value
            print(
                f"[WORKER] Processing pipeline {pipeline.id} "
                f"(ticket #{pipeline.ticket_id}, state={state_val})",
                flush=True,
            )
            logger.info("Processing pipeline %s", pipeline.id)

            # Create adapters for this pipeline
            kanban = KanbanAdapter(
                repo=project.repo,
                project_number=project.github_project_id,
                token=token,
            )
            git_manager = GitManager(
                repo=project.repo,
                token=token,
                repo_path=repo_path,
            )
            testing_runner = TestingRunner(
                git_manager=git_manager,
                poll_interval=30,
            )

            try:
                msg = f"[WORKER] Calling orchestrator.process_pipeline for {pipeline.id}"
                print(msg, flush=True)
                # Process the pipeline through its current state
                orchestrator.process_pipeline(
                    pipeline_id=pipeline.id,
                    git_manager=git_manager,
                    kanban=kanban,
                    coder_worker=coder_worker,
                    testing_runner=testing_runner,
                    repo_path=repo_path,
                )
                print(f"[WORKER] Finished processing pipeline {pipeline.id}", flush=True)
            except Exception as e:
                print(f"[WORKER] ERROR processing pipeline {pipeline.id}: {e}", flush=True)
                logger.exception("Error processing pipeline %s: %s", pipeline.id, e)
            finally:
                kanban.close()
                git_manager.close()

            # Small delay before next iteration
            time.sleep(2)

    except Exception as e:
        logger.exception("Worker error for project %s: %s", project_id, e)
        orchestrator.stop_autopilot(project_id, reason=f"worker_error: {e}")
    finally:
        logger.info("Worker stopped for project %s", project_id)


def start_worker(
    project_id: str,
    state_store: StateStore,
    orchestrator: Orchestrator,
    repo_path: str = ".",
    max_concurrent: int = 1,
) -> None:
    """Start a background worker for a project using threading."""
    # Stop existing worker if any
    stop_worker(project_id)

    # Create and start worker thread
    thread = threading.Thread(
        target=start_worker_sync,
        args=(project_id, state_store, orchestrator, repo_path, max_concurrent),
        daemon=True,
    )
    thread.start()
    _worker_tasks[project_id] = thread
    logger.info("Started worker thread for project %s", project_id)


def stop_worker(project_id: str) -> None:
    """Stop the background worker for a project."""
    if project_id in _worker_tasks:
        # Thread will stop on next iteration when autopilot is set to False
        del _worker_tasks[project_id]
        logger.info("Stopped worker for project %s", project_id)
