"""Sync endpoint for manual queue processing."""

from fastapi import APIRouter

from vibecc.api.dependencies import SchedulerDep, StateStoreDep
from vibecc.api.models import (
    APIResponse,
    SyncResultResponse,
    pipeline_to_response,
)

router = APIRouter(tags=["sync"])


@router.post(
    "/projects/{project_id}/sync",
    response_model=APIResponse[SyncResultResponse],
)
def sync_queue(
    project_id: str, store: StateStoreDep, scheduler: SchedulerDep
) -> APIResponse[SyncResultResponse]:
    """Process the queue once, starting pipelines up to available capacity."""
    # Verify project exists (will raise ProjectNotFoundError if not)
    store.get_project(project_id)

    result = scheduler.sync(project_id)
    return APIResponse(
        data=SyncResultResponse(
            started=[pipeline_to_response(p) for p in result.started],
            remaining=result.remaining,
        )
    )
