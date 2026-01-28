"""StateStore - Main API for State Store operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from vibecc.state_store.database import Database
from vibecc.state_store.exceptions import (
    ProjectExistsError,
    ProjectHasActivePipelinesError,
    ProjectNotFoundError,
)
from vibecc.state_store.models import Pipeline, PipelineState, Project


class StateStore:
    """Main API for State Store operations.

    Provides CRUD operations for Projects, Pipelines, and History.
    """

    def __init__(self, db_path: str = "vibecc.db") -> None:
        """Initialize State Store with SQLite database.

        Creates database and tables if they don't exist.

        Args:
            db_path: Path to SQLite database file
        """
        self._db = Database(db_path)
        self._db.create_tables()

    def close(self) -> None:
        """Close the database connection."""
        self._db.close()

    # --- Project Operations ---

    def create_project(
        self,
        name: str,
        repo: str,
        base_branch: str = "main",
        github_project_id: int | None = None,
        max_retries_ci: int = 3,
        max_retries_review: int = 3,
    ) -> Project:
        """Create a new project.

        Args:
            name: Human-readable project name
            repo: GitHub repo in "owner/repo" format
            base_branch: Branch to create feature branches from
            github_project_id: GitHub Projects board ID (for kanban)
            max_retries_ci: Max CI failure retries before FAILED
            max_retries_review: Max review failure retries before FAILED

        Returns:
            Created Project object with generated ID

        Raises:
            ProjectExistsError: If project with same repo already exists
        """
        session = self._db.get_session()
        try:
            project = Project(
                name=name,
                repo=repo,
                base_branch=base_branch,
                github_project_id=github_project_id,
                max_retries_ci=max_retries_ci,
                max_retries_review=max_retries_review,
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            return project
        except IntegrityError as e:
            session.rollback()
            if "UNIQUE constraint failed" in str(e) or "projects.repo" in str(e):
                raise ProjectExistsError(f"Project with repo '{repo}' already exists") from e
            raise
        finally:
            session.close()

    def get_project(self, project_id: str) -> Project:
        """Get project by ID.

        Args:
            project_id: The project's unique ID

        Returns:
            The Project object

        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        session = self._db.get_session()
        try:
            project = session.get(Project, project_id)
            if project is None:
                raise ProjectNotFoundError(f"Project with id '{project_id}' not found")
            return project
        finally:
            session.close()

    def get_project_by_repo(self, repo: str) -> Project:
        """Get project by repo name.

        Args:
            repo: GitHub repo in "owner/repo" format

        Returns:
            The Project object

        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        session = self._db.get_session()
        try:
            stmt = select(Project).where(Project.repo == repo)
            project = session.execute(stmt).scalar_one_or_none()
            if project is None:
                raise ProjectNotFoundError(f"Project with repo '{repo}' not found")
            return project
        finally:
            session.close()

    def list_projects(self) -> list[Project]:
        """List all projects.

        Returns:
            List of all projects, ordered by name
        """
        session = self._db.get_session()
        try:
            stmt = select(Project).order_by(Project.name)
            result = session.execute(stmt)
            return list(result.scalars().all())
        finally:
            session.close()

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        base_branch: str | None = None,
        github_project_id: int | None = None,
        max_retries_ci: int | None = None,
        max_retries_review: int | None = None,
    ) -> Project:
        """Update project fields. Only provided fields are updated.

        Args:
            project_id: The project's unique ID
            name: New project name (optional)
            base_branch: New base branch (optional)
            github_project_id: New GitHub project ID (optional)
            max_retries_ci: New max CI retries (optional)
            max_retries_review: New max review retries (optional)

        Returns:
            The updated Project object

        Raises:
            ProjectNotFoundError: If project doesn't exist
        """
        session = self._db.get_session()
        try:
            project = session.get(Project, project_id)
            if project is None:
                raise ProjectNotFoundError(f"Project with id '{project_id}' not found")

            if name is not None:
                project.name = name
            if base_branch is not None:
                project.base_branch = base_branch
            if github_project_id is not None:
                project.github_project_id = github_project_id
            if max_retries_ci is not None:
                project.max_retries_ci = max_retries_ci
            if max_retries_review is not None:
                project.max_retries_review = max_retries_review

            session.commit()
            session.refresh(project)
            return project
        finally:
            session.close()

    def delete_project(self, project_id: str) -> None:
        """Delete a project. Fails if project has active pipelines.

        Args:
            project_id: The project's unique ID

        Raises:
            ProjectNotFoundError: If project doesn't exist
            ProjectHasActivePipelinesError: If project has active pipelines
        """
        session = self._db.get_session()
        try:
            project = session.get(Project, project_id)
            if project is None:
                raise ProjectNotFoundError(f"Project with id '{project_id}' not found")

            # Check for active pipelines (not MERGED or FAILED)
            active_states = [
                PipelineState.QUEUED.value,
                PipelineState.CODING.value,
                PipelineState.TESTING.value,
                PipelineState.REVIEW.value,
            ]
            stmt = select(Pipeline).where(
                Pipeline.project_id == project_id,
                Pipeline.state.in_(active_states),
            )
            active_pipeline = session.execute(stmt).scalar_one_or_none()
            if active_pipeline is not None:
                raise ProjectHasActivePipelinesError(f"Project '{project_id}' has active pipelines")

            session.delete(project)
            session.commit()
        finally:
            session.close()
