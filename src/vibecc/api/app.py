"""FastAPI application setup."""

from __future__ import annotations

import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vibecc.api.dependencies import (
    close_orchestrator,
    close_scheduler,
    close_state_store,
    init_event_manager,
    init_orchestrator,
    init_scheduler,
    init_state_store,
)
from vibecc.api.models import APIResponse
from vibecc.api.routes import control, events, history, pipelines, projects, sync
from vibecc.state_store import (
    PipelineNotFoundError,
    ProjectExistsError,
    ProjectHasActivePipelinesError,
    ProjectNotFoundError,
    StateStoreError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from vibecc.orchestrator import Orchestrator
    from vibecc.scheduler import SyncResult
    from vibecc.state_store import StateStore


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


class AppScheduler:
    """App-level scheduler wrapper matching SchedulerProtocol.

    Creates KanbanAdapter and GitManager per project and delegates to the real Scheduler.
    """

    def __init__(
        self,
        state_store: StateStore,
        orchestrator: Orchestrator,
        token: str,
        repo_path: str | Path = ".",
    ) -> None:
        from vibecc.scheduler import Scheduler  # noqa: PLC0415

        self._state_store = state_store
        self._orchestrator = orchestrator
        self._token = token
        self._repo_path = Path(repo_path)
        self._scheduler = Scheduler(
            state_store=state_store,
            orchestrator=orchestrator,
            max_concurrent=1,
        )

    def sync(self, project_id: str) -> SyncResult:
        from vibecc.git_manager import GitManager  # noqa: PLC0415
        from vibecc.kanban import KanbanAdapter  # noqa: PLC0415
        from vibecc.scheduler import SyncResult  # noqa: PLC0415, F401

        project = self._state_store.get_project(project_id)

        if not self._token:
            raise RuntimeError("GitHub token not configured")
        if not project.github_project_id:
            raise RuntimeError(f"Project {project.name} has no github_project_id configured")

        kanban = KanbanAdapter(
            repo=project.repo,
            project_number=project.github_project_id,
            token=self._token,
        )
        git_manager = GitManager(
            repo=project.repo,
            token=self._token,
            repo_path=self._repo_path,
        )

        try:
            return self._scheduler.sync(project_id, kanban, git_manager)
        finally:
            kanban.close()
            git_manager.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    from vibecc.orchestrator import Orchestrator  # noqa: PLC0415

    # Startup
    db_path = app.state.db_path if hasattr(app.state, "db_path") else "vibecc.db"
    repo_path = app.state.repo_path if hasattr(app.state, "repo_path") else "."
    store = init_state_store(db_path)
    event_manager = init_event_manager()

    orchestrator = Orchestrator(state_store=store, event_manager=event_manager)
    init_orchestrator(orchestrator)

    token = _get_github_token()
    scheduler = AppScheduler(
        state_store=store,
        orchestrator=orchestrator,
        token=token,
        repo_path=repo_path,
    )
    init_scheduler(scheduler)

    yield
    # Shutdown
    close_scheduler()
    close_orchestrator()
    close_state_store()


def create_app(db_path: str = "vibecc.db", repo_path: str = ".") -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="VibeCC API",
        description="REST API for VibeCC - Code Compilation Pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store config for lifespan manager
    app.state.db_path = db_path
    app.state.repo_path = repo_path

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(
        _request: Request, _exc: ProjectNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse[None](data=None, error="Project not found").model_dump(),
        )

    @app.exception_handler(PipelineNotFoundError)
    async def pipeline_not_found_handler(
        _request: Request, _exc: PipelineNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse[None](data=None, error="Pipeline not found").model_dump(),
        )

    @app.exception_handler(ProjectExistsError)
    async def project_exists_handler(_request: Request, _exc: ProjectExistsError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=APIResponse[None](
                data=None, error="Project with this repo already exists"
            ).model_dump(),
        )

    @app.exception_handler(ProjectHasActivePipelinesError)
    async def project_has_pipelines_handler(
        _request: Request, _exc: ProjectHasActivePipelinesError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=APIResponse[None](
                data=None, error="Cannot delete project with active pipelines"
            ).model_dump(),
        )

    @app.exception_handler(StateStoreError)
    async def state_store_error_handler(_request: Request, _exc: StateStoreError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse[None](data=None, error="Internal server error").model_dump(),
        )

    # Include routers
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(pipelines.router, prefix="/api/v1")
    app.include_router(history.router, prefix="/api/v1")
    app.include_router(control.router, prefix="/api/v1")
    app.include_router(sync.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")

    return app


# Default app instance
app = create_app()
