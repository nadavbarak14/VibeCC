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
