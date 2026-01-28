"""StateStore - Main API for State Store operations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from vibecc.state_store.database import Database
from vibecc.state_store.exceptions import (
    PipelineExistsError,
    PipelineNotFoundError,
    ProjectExistsError,
    ProjectHasActivePipelinesError,
    ProjectNotFoundError,
)
from vibecc.state_store.models import (
    HistoryStats,
    Pipeline,
    PipelineHistory,
    PipelineState,
    Project,
)


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

    # --- Pipeline Operations ---

    def create_pipeline(
        self,
        project_id: str,
        ticket_id: str,
        ticket_title: str,
        branch_name: str,
        ticket_body: str = "",
    ) -> Pipeline:
        """Create a new pipeline.

        Args:
            project_id: The project's unique ID
            ticket_id: The ticket/issue ID
            ticket_title: Title of the ticket
            branch_name: Git branch name for this pipeline
            ticket_body: Body/description of the ticket

        Returns:
            Created Pipeline object with generated ID

        Raises:
            ProjectNotFoundError: If project doesn't exist
            PipelineExistsError: If pipeline for this ticket already exists in project
        """
        session = self._db.get_session()
        try:
            # Verify project exists
            project = session.get(Project, project_id)
            if project is None:
                raise ProjectNotFoundError(f"Project with id '{project_id}' not found")

            # Check for duplicate ticket in same project
            stmt = select(Pipeline).where(
                Pipeline.project_id == project_id,
                Pipeline.ticket_id == ticket_id,
            )
            existing = session.execute(stmt).scalar_one_or_none()
            if existing is not None:
                raise PipelineExistsError(
                    f"Pipeline for ticket '{ticket_id}' already exists in project '{project_id}'"
                )

            pipeline = Pipeline(
                project_id=project_id,
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                branch_name=branch_name,
                ticket_body=ticket_body,
            )
            session.add(pipeline)
            session.commit()
            session.refresh(pipeline)
            return pipeline
        finally:
            session.close()

    def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """Get pipeline by ID.

        Args:
            pipeline_id: The pipeline's unique ID

        Returns:
            The Pipeline object

        Raises:
            PipelineNotFoundError: If pipeline doesn't exist
        """
        session = self._db.get_session()
        try:
            pipeline = session.get(Pipeline, pipeline_id)
            if pipeline is None:
                raise PipelineNotFoundError(f"Pipeline with id '{pipeline_id}' not found")
            return pipeline
        finally:
            session.close()

    def get_pipeline_by_ticket(self, project_id: str, ticket_id: str) -> Pipeline:
        """Get pipeline by project and ticket ID.

        Args:
            project_id: The project's unique ID
            ticket_id: The ticket/issue ID

        Returns:
            The Pipeline object

        Raises:
            PipelineNotFoundError: If pipeline doesn't exist
        """
        session = self._db.get_session()
        try:
            stmt = select(Pipeline).where(
                Pipeline.project_id == project_id,
                Pipeline.ticket_id == ticket_id,
            )
            pipeline = session.execute(stmt).scalar_one_or_none()
            if pipeline is None:
                raise PipelineNotFoundError(
                    f"Pipeline for ticket '{ticket_id}' not found in project '{project_id}'"
                )
            return pipeline
        finally:
            session.close()

    def list_pipelines(
        self,
        project_id: str | None = None,
        state: PipelineState | None = None,
    ) -> list[Pipeline]:
        """List pipelines with optional filters.

        Args:
            project_id: Filter by project ID (optional)
            state: Filter by pipeline state (optional)

        Returns:
            List of pipelines, ordered by created_at descending (most recent first)
        """
        session = self._db.get_session()
        try:
            stmt = select(Pipeline)

            if project_id is not None:
                stmt = stmt.where(Pipeline.project_id == project_id)
            if state is not None:
                stmt = stmt.where(Pipeline.state == state.value)

            stmt = stmt.order_by(Pipeline.created_at.desc())
            result = session.execute(stmt)
            return list(result.scalars().all())
        finally:
            session.close()

    def update_pipeline(
        self,
        pipeline_id: str,
        state: PipelineState | None = None,
        pr_id: int | None = None,
        pr_url: str | None = None,
        retry_count_ci: int | None = None,
        retry_count_review: int | None = None,
        feedback: str | None = None,
    ) -> Pipeline:
        """Update pipeline fields. Only provided fields are updated.

        Args:
            pipeline_id: The pipeline's unique ID
            state: New pipeline state (optional)
            pr_id: PR number (optional)
            pr_url: PR URL (optional)
            retry_count_ci: CI retry count (optional)
            retry_count_review: Review retry count (optional)
            feedback: Feedback from CI/review failure (optional)

        Returns:
            The updated Pipeline object

        Raises:
            PipelineNotFoundError: If pipeline doesn't exist
        """
        session = self._db.get_session()
        try:
            pipeline = session.get(Pipeline, pipeline_id)
            if pipeline is None:
                raise PipelineNotFoundError(f"Pipeline with id '{pipeline_id}' not found")

            if state is not None:
                pipeline.state = state.value
            if pr_id is not None:
                pipeline.pr_id = pr_id
            if pr_url is not None:
                pipeline.pr_url = pr_url
            if retry_count_ci is not None:
                pipeline.retry_count_ci = retry_count_ci
            if retry_count_review is not None:
                pipeline.retry_count_review = retry_count_review
            if feedback is not None:
                pipeline.feedback = feedback

            session.commit()
            session.refresh(pipeline)
            return pipeline
        finally:
            session.close()

    def delete_pipeline(self, pipeline_id: str) -> None:
        """Delete a pipeline.

        Args:
            pipeline_id: The pipeline's unique ID

        Raises:
            PipelineNotFoundError: If pipeline doesn't exist
        """
        session = self._db.get_session()
        try:
            pipeline = session.get(Pipeline, pipeline_id)
            if pipeline is None:
                raise PipelineNotFoundError(f"Pipeline with id '{pipeline_id}' not found")

            session.delete(pipeline)
            session.commit()
        finally:
            session.close()

    # --- History Operations ---

    def save_to_history(self, pipeline: Pipeline) -> PipelineHistory:
        """Move completed pipeline to history.

        Copies pipeline data to history table with completion timestamp.
        Does NOT delete the original pipeline (caller should do that).

        Args:
            pipeline: The completed pipeline (state should be MERGED or FAILED)

        Returns:
            Created PipelineHistory object
        """
        session = self._db.get_session()
        try:
            completed_at = datetime.now(UTC)
            started_at = pipeline.created_at.replace(tzinfo=UTC)
            duration_seconds = int((completed_at - started_at).total_seconds())

            history = PipelineHistory(
                project_id=pipeline.project_id,
                ticket_id=pipeline.ticket_id,
                ticket_title=pipeline.ticket_title,
                final_state=pipeline.state,
                branch_name=pipeline.branch_name,
                pr_id=pipeline.pr_id,
                pr_url=pipeline.pr_url,
                total_retries_ci=pipeline.retry_count_ci,
                total_retries_review=pipeline.retry_count_review,
                started_at=pipeline.created_at,
                duration_seconds=duration_seconds,
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history
        finally:
            session.close()

    def get_history(
        self,
        project_id: str | None = None,
        final_state: PipelineState | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineHistory]:
        """Query pipeline history.

        Args:
            project_id: Filter by project (None = all)
            final_state: Filter by final state (None = all)
            limit: Max results to return
            offset: Offset for pagination

        Returns:
            List of historical pipelines, ordered by completed_at desc
        """
        session = self._db.get_session()
        try:
            stmt = select(PipelineHistory)

            if project_id is not None:
                stmt = stmt.where(PipelineHistory.project_id == project_id)
            if final_state is not None:
                stmt = stmt.where(PipelineHistory.final_state == final_state.value)

            stmt = stmt.order_by(PipelineHistory.completed_at.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = session.execute(stmt)
            return list(result.scalars().all())
        finally:
            session.close()

    def get_history_stats(
        self,
        project_id: str | None = None,
    ) -> HistoryStats:
        """Get aggregated stats from history.

        Args:
            project_id: Filter by project (None = all)

        Returns:
            HistoryStats with counts, averages, etc.
        """
        session = self._db.get_session()
        try:
            # Build base query
            stmt = select(
                func.count(PipelineHistory.id).label("total"),
                func.sum(
                    case(
                        (PipelineHistory.final_state == PipelineState.MERGED.value, 1),
                        else_=0,
                    )
                ).label("merged"),
                func.sum(
                    case(
                        (PipelineHistory.final_state == PipelineState.FAILED.value, 1),
                        else_=0,
                    )
                ).label("failed"),
                func.avg(PipelineHistory.duration_seconds).label("avg_duration"),
                func.avg(PipelineHistory.total_retries_ci).label("avg_ci"),
                func.avg(PipelineHistory.total_retries_review).label("avg_review"),
            )

            if project_id is not None:
                stmt = stmt.where(PipelineHistory.project_id == project_id)

            result = session.execute(stmt).one()

            return HistoryStats(
                total_completed=result.total or 0,
                total_merged=result.merged or 0,
                total_failed=result.failed or 0,
                avg_duration_seconds=float(result.avg_duration or 0.0),
                avg_retries_ci=float(result.avg_ci or 0.0),
                avg_retries_review=float(result.avg_review or 0.0),
            )
        finally:
            session.close()
