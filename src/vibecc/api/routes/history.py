"""History query endpoints."""

from fastapi import APIRouter, Query

from vibecc.api.dependencies import StateStoreDep
from vibecc.api.models import (
    APIResponse,
    HistoryResponse,
    HistoryStatsResponse,
    history_stats_to_response,
    history_to_response,
)
from vibecc.state_store import PipelineState

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=APIResponse[list[HistoryResponse]])
def list_history(
    store: StateStoreDep,
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    final_state: str | None = Query(default=None, description="Filter by final state"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> APIResponse[list[HistoryResponse]]:
    """List pipeline history with optional filters and pagination."""
    pipeline_state = PipelineState(final_state) if final_state else None
    history = store.get_history(
        project_id=project_id,
        final_state=pipeline_state,
        limit=limit,
        offset=offset,
    )
    return APIResponse(data=[history_to_response(h) for h in history])


@router.get("/stats", response_model=APIResponse[HistoryStatsResponse])
def get_history_stats(
    store: StateStoreDep,
    project_id: str | None = Query(default=None, description="Filter by project ID"),
) -> APIResponse[HistoryStatsResponse]:
    """Get aggregated history statistics."""
    stats = store.get_history_stats(project_id=project_id)
    return APIResponse(data=history_stats_to_response(stats))
