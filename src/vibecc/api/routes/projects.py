"""Project CRUD endpoints."""

from fastapi import APIRouter, status

from vibecc.api.dependencies import StateStoreDep
from vibecc.api.models import (
    APIResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    project_to_response,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=APIResponse[list[ProjectResponse]])
def list_projects(store: StateStoreDep) -> APIResponse[list[ProjectResponse]]:
    """List all projects."""
    projects = store.list_projects()
    return APIResponse(data=[project_to_response(p) for p in projects])


@router.post(
    "",
    response_model=APIResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_project(project: ProjectCreate, store: StateStoreDep) -> APIResponse[ProjectResponse]:
    """Create a new project."""
    created = store.create_project(
        name=project.name,
        repo=project.repo,
        base_branch=project.base_branch,
        github_project_id=project.github_project_id,
        max_retries_ci=project.max_retries_ci,
        max_retries_review=project.max_retries_review,
    )
    return APIResponse(data=project_to_response(created))


@router.get("/{project_id}", response_model=APIResponse[ProjectResponse])
def get_project(project_id: str, store: StateStoreDep) -> APIResponse[ProjectResponse]:
    """Get a project by ID."""
    project = store.get_project(project_id)
    return APIResponse(data=project_to_response(project))


@router.patch("/{project_id}", response_model=APIResponse[ProjectResponse])
def update_project(
    project_id: str, project: ProjectUpdate, store: StateStoreDep
) -> APIResponse[ProjectResponse]:
    """Update a project (partial update)."""
    updated = store.update_project(
        project_id,
        name=project.name,
        base_branch=project.base_branch,
        github_project_id=project.github_project_id,
        max_retries_ci=project.max_retries_ci,
        max_retries_review=project.max_retries_review,
    )
    return APIResponse(data=project_to_response(updated))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, store: StateStoreDep) -> None:
    """Delete a project."""
    store.delete_project(project_id)
