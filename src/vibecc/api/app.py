"""FastAPI application setup."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vibecc.api.dependencies import close_state_store, init_state_store
from vibecc.api.models import APIResponse
from vibecc.api.routes import projects
from vibecc.state_store import (
    ProjectExistsError,
    ProjectHasActivePipelinesError,
    ProjectNotFoundError,
    StateStoreError,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    db_path = app.state.db_path if hasattr(app.state, "db_path") else "vibecc.db"
    init_state_store(db_path)
    yield
    # Shutdown
    close_state_store()


def create_app(db_path: str = "vibecc.db") -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="VibeCC API",
        description="REST API for VibeCC - Code Compilation Pipeline",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Store db_path for lifespan manager
    app.state.db_path = db_path

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

    return app


# Default app instance
app = create_app()
