"""Control endpoints for Orchestrator (autopilot)."""

from fastapi import APIRouter

from vibecc.api.dependencies import OrchestratorDep, StateStoreDep
from vibecc.api.models import (
    APIResponse,
    AutopilotActionResponse,
    AutopilotStatusResponse,
    autopilot_status_to_response,
)
from vibecc.api.worker import start_worker, stop_worker

router = APIRouter(tags=["control"])


@router.get(
    "/projects/{project_id}/autopilot",
    response_model=APIResponse[AutopilotStatusResponse],
)
def get_autopilot_status(
    project_id: str, store: StateStoreDep, orchestrator: OrchestratorDep
) -> APIResponse[AutopilotStatusResponse]:
    """Get autopilot status for a project."""
    # Verify project exists (will raise ProjectNotFoundError if not)
    store.get_project(project_id)

    status = orchestrator.get_autopilot_status(project_id)
    return APIResponse(data=autopilot_status_to_response(status))


@router.post(
    "/projects/{project_id}/autopilot/start",
    response_model=APIResponse[AutopilotActionResponse],
)
def start_autopilot(
    project_id: str,
    store: StateStoreDep,
    orchestrator: OrchestratorDep,
) -> APIResponse[AutopilotActionResponse]:
    """Start autopilot for a project."""
    # Verify project exists (will raise ProjectNotFoundError if not)
    store.get_project(project_id)

    orchestrator.start_autopilot(project_id)

    # Start background worker to process pipelines
    start_worker(
        project_id=project_id,
        state_store=store,
        orchestrator=orchestrator,  # type: ignore[arg-type]
        repo_path=".",
        max_concurrent=1,
    )

    return APIResponse(data=AutopilotActionResponse(message="Autopilot started"))


@router.post(
    "/projects/{project_id}/autopilot/stop",
    response_model=APIResponse[AutopilotActionResponse],
)
def stop_autopilot(
    project_id: str, store: StateStoreDep, orchestrator: OrchestratorDep
) -> APIResponse[AutopilotActionResponse]:
    """Stop autopilot for a project."""
    # Verify project exists (will raise ProjectNotFoundError if not)
    store.get_project(project_id)

    orchestrator.stop_autopilot(project_id)

    # Stop the background worker
    stop_worker(project_id)

    return APIResponse(data=AutopilotActionResponse(message="Autopilot stopped"))
