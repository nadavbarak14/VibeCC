"""Pipeline query endpoints."""

from fastapi import APIRouter, Query

from vibecc.api.dependencies import StateStoreDep
from vibecc.api.models import (
    APIResponse,
    PipelineResponse,
    pipeline_to_response,
)
from vibecc.state_store import PipelineState

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.get("", response_model=APIResponse[list[PipelineResponse]])
def list_pipelines(
    store: StateStoreDep,
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    state: str | None = Query(default=None, description="Filter by state"),
) -> APIResponse[list[PipelineResponse]]:
    """List pipelines with optional filters."""
    pipeline_state = PipelineState(state) if state else None
    pipelines = store.list_pipelines(project_id=project_id, state=pipeline_state)
    return APIResponse(data=[pipeline_to_response(p) for p in pipelines])


@router.get("/{pipeline_id}", response_model=APIResponse[PipelineResponse])
def get_pipeline(pipeline_id: str, store: StateStoreDep) -> APIResponse[PipelineResponse]:
    """Get a pipeline by ID."""
    pipeline = store.get_pipeline(pipeline_id)
    return APIResponse(data=pipeline_to_response(pipeline))
