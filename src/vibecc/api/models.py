"""Pydantic models for REST API."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    data: T | None = None
    error: str | None = None


# Project models


class ProjectCreate(BaseModel):
    """Request model for creating a project."""

    name: str = Field(..., min_length=1, max_length=255)
    repo: str = Field(..., min_length=3, max_length=255, pattern=r"^[\w\-\.]+/[\w\-\.]+$")
    base_branch: str = Field(default="main", max_length=255)
    github_project_id: int | None = None
    max_retries_ci: int = Field(default=3, ge=0, le=10)
    max_retries_review: int = Field(default=3, ge=0, le=10)


class ProjectUpdate(BaseModel):
    """Request model for updating a project (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_branch: str | None = Field(default=None, max_length=255)
    github_project_id: int | None = None
    max_retries_ci: int | None = Field(default=None, ge=0, le=10)
    max_retries_review: int | None = Field(default=None, ge=0, le=10)


class ProjectResponse(BaseModel):
    """Response model for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    repo: str
    base_branch: str
    github_project_id: int | None
    max_retries_ci: int
    max_retries_review: int
    created_at: datetime
    updated_at: datetime


def project_to_response(project: Any) -> ProjectResponse:
    """Convert a Project model to ProjectResponse."""
    return ProjectResponse.model_validate(project)


# Pipeline models


class PipelineResponse(BaseModel):
    """Response model for a pipeline."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    ticket_id: str
    ticket_title: str
    ticket_body: str
    state: str
    branch_name: str
    pr_id: int | None
    pr_url: str | None
    retry_count_ci: int
    retry_count_review: int
    feedback: str | None
    created_at: datetime
    updated_at: datetime


def pipeline_to_response(pipeline: Any) -> PipelineResponse:
    """Convert a Pipeline model to PipelineResponse."""
    return PipelineResponse.model_validate(pipeline)


# History models


class HistoryResponse(BaseModel):
    """Response model for a pipeline history entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    ticket_id: str
    ticket_title: str
    final_state: str
    branch_name: str
    pr_id: int | None
    pr_url: str | None
    total_retries_ci: int
    total_retries_review: int
    started_at: datetime
    completed_at: datetime
    duration_seconds: int


def history_to_response(history: Any) -> HistoryResponse:
    """Convert a PipelineHistory model to HistoryResponse."""
    return HistoryResponse.model_validate(history)


class HistoryStatsResponse(BaseModel):
    """Response model for history statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_completed: int
    total_merged: int
    total_failed: int
    avg_duration_seconds: float
    avg_retries_ci: float
    avg_retries_review: float


def history_stats_to_response(stats: Any) -> HistoryStatsResponse:
    """Convert a HistoryStats model to HistoryStatsResponse."""
    return HistoryStatsResponse.model_validate(stats)


# Autopilot/Control models


class AutopilotStatusResponse(BaseModel):
    """Response model for autopilot status."""

    model_config = ConfigDict(from_attributes=True)

    project_id: str
    running: bool
    active_pipelines: int
    queued_tickets: int


def autopilot_status_to_response(status: Any) -> AutopilotStatusResponse:
    """Convert an AutopilotStatus to AutopilotStatusResponse."""
    return AutopilotStatusResponse.model_validate(status)


class AutopilotActionResponse(BaseModel):
    """Response model for autopilot actions (start/stop)."""

    message: str
