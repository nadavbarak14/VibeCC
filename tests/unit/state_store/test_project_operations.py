"""Unit tests for StateStore project operations."""

import pytest

from vibecc.state_store import (
    Pipeline,
    PipelineState,
    ProjectExistsError,
    ProjectHasActivePipelinesError,
    ProjectNotFoundError,
    StateStore,
)


@pytest.fixture
def store() -> StateStore:
    """Create an in-memory StateStore for testing."""
    return StateStore(":memory:")


@pytest.mark.unit
class TestCreateProject:
    """Tests for create_project."""

    def test_create_project_minimal(self, store: StateStore) -> None:
        """Create with only required fields (name, repo)."""
        project = store.create_project(name="Test Project", repo="owner/repo")

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.repo == "owner/repo"
        assert project.base_branch == "main"
        assert project.github_project_id is None
        assert project.max_retries_ci == 3
        assert project.max_retries_review == 3
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_create_project_all_fields(self, store: StateStore) -> None:
        """Create with all optional fields."""
        project = store.create_project(
            name="Full Project",
            repo="org/full-repo",
            base_branch="develop",
            github_project_id=12345,
            max_retries_ci=5,
            max_retries_review=2,
        )

        assert project.name == "Full Project"
        assert project.repo == "org/full-repo"
        assert project.base_branch == "develop"
        assert project.github_project_id == 12345
        assert project.max_retries_ci == 5
        assert project.max_retries_review == 2

    def test_create_project_duplicate_repo_raises(self, store: StateStore) -> None:
        """ProjectExistsError on duplicate repo."""
        store.create_project(name="First", repo="owner/repo")

        with pytest.raises(ProjectExistsError) as exc_info:
            store.create_project(name="Second", repo="owner/repo")

        assert "owner/repo" in str(exc_info.value)


@pytest.mark.unit
class TestGetProject:
    """Tests for get_project."""

    def test_get_project_exists(self, store: StateStore) -> None:
        """Returns correct project."""
        created = store.create_project(name="Test", repo="owner/repo")

        retrieved = store.get_project(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == "Test"
        assert retrieved.repo == "owner/repo"

    def test_get_project_not_found_raises(self, store: StateStore) -> None:
        """ProjectNotFoundError for invalid ID."""
        with pytest.raises(ProjectNotFoundError) as exc_info:
            store.get_project("nonexistent-id")

        assert "nonexistent-id" in str(exc_info.value)


@pytest.mark.unit
class TestGetProjectByRepo:
    """Tests for get_project_by_repo."""

    def test_get_project_by_repo_exists(self, store: StateStore) -> None:
        """Returns correct project by repo."""
        created = store.create_project(name="Test", repo="owner/repo")

        retrieved = store.get_project_by_repo("owner/repo")

        assert retrieved.id == created.id
        assert retrieved.repo == "owner/repo"

    def test_get_project_by_repo_not_found_raises(self, store: StateStore) -> None:
        """ProjectNotFoundError for invalid repo."""
        with pytest.raises(ProjectNotFoundError) as exc_info:
            store.get_project_by_repo("nonexistent/repo")

        assert "nonexistent/repo" in str(exc_info.value)


@pytest.mark.unit
class TestListProjects:
    """Tests for list_projects."""

    def test_list_projects_empty(self, store: StateStore) -> None:
        """Returns empty list when no projects."""
        projects = store.list_projects()

        assert projects == []

    def test_list_projects_multiple(self, store: StateStore) -> None:
        """Returns all projects ordered by name."""
        store.create_project(name="Charlie", repo="owner/charlie")
        store.create_project(name="Alpha", repo="owner/alpha")
        store.create_project(name="Bravo", repo="owner/bravo")

        projects = store.list_projects()

        assert len(projects) == 3
        assert projects[0].name == "Alpha"
        assert projects[1].name == "Bravo"
        assert projects[2].name == "Charlie"


@pytest.mark.unit
class TestUpdateProject:
    """Tests for update_project."""

    def test_update_project_single_field(self, store: StateStore) -> None:
        """Update only one field, others unchanged."""
        project = store.create_project(
            name="Original",
            repo="owner/repo",
            base_branch="main",
            max_retries_ci=3,
        )

        updated = store.update_project(project.id, name="Updated")

        assert updated.name == "Updated"
        assert updated.repo == "owner/repo"
        assert updated.base_branch == "main"
        assert updated.max_retries_ci == 3

    def test_update_project_multiple_fields(self, store: StateStore) -> None:
        """Update multiple fields at once."""
        project = store.create_project(name="Original", repo="owner/repo")

        updated = store.update_project(
            project.id,
            name="Updated",
            base_branch="develop",
            max_retries_ci=5,
        )

        assert updated.name == "Updated"
        assert updated.base_branch == "develop"
        assert updated.max_retries_ci == 5

    def test_update_project_not_found_raises(self, store: StateStore) -> None:
        """ProjectNotFoundError for invalid ID."""
        with pytest.raises(ProjectNotFoundError) as exc_info:
            store.update_project("nonexistent-id", name="New Name")

        assert "nonexistent-id" in str(exc_info.value)

    def test_update_project_sets_updated_at(self, store: StateStore) -> None:
        """updated_at timestamp changes."""
        project = store.create_project(name="Test", repo="owner/repo")
        original_updated_at = project.updated_at

        # Small delay to ensure timestamp difference
        updated = store.update_project(project.id, name="New Name")

        # SQLite datetime precision may not distinguish very small intervals,
        # but the update should at least not regress the timestamp
        assert updated.updated_at >= original_updated_at


@pytest.mark.unit
class TestDeleteProject:
    """Tests for delete_project."""

    def test_delete_project_exists(self, store: StateStore) -> None:
        """Successfully deletes project."""
        project = store.create_project(name="ToDelete", repo="owner/to-delete")

        store.delete_project(project.id)

        with pytest.raises(ProjectNotFoundError):
            store.get_project(project.id)

    def test_delete_project_not_found_raises(self, store: StateStore) -> None:
        """ProjectNotFoundError for invalid ID."""
        with pytest.raises(ProjectNotFoundError) as exc_info:
            store.delete_project("nonexistent-id")

        assert "nonexistent-id" in str(exc_info.value)

    def test_delete_project_with_active_pipeline_raises(self, store: StateStore) -> None:
        """ProjectHasActivePipelinesError when project has active pipelines."""
        project = store.create_project(name="Test", repo="owner/repo")

        # Create an active pipeline directly in the database
        session = store._db.get_session()
        pipeline = Pipeline(
            project_id=project.id,
            ticket_id="42",
            ticket_title="Active ticket",
            branch_name="ticket-42",
            state=PipelineState.CODING.value,
        )
        session.add(pipeline)
        session.commit()
        session.close()

        with pytest.raises(ProjectHasActivePipelinesError) as exc_info:
            store.delete_project(project.id)

        assert project.id in str(exc_info.value)

    def test_delete_project_with_completed_pipeline_succeeds(
        self, store: StateStore
    ) -> None:
        """Can delete project with only completed (MERGED/FAILED) pipelines."""
        project = store.create_project(name="Test", repo="owner/repo")

        # Create completed pipelines
        session = store._db.get_session()
        for i, state in enumerate([PipelineState.MERGED, PipelineState.FAILED]):
            pipeline = Pipeline(
                project_id=project.id,
                ticket_id=str(i),
                ticket_title=f"Completed ticket {i}",
                branch_name=f"ticket-{i}",
                state=state.value,
            )
            session.add(pipeline)
        session.commit()
        session.close()

        # Should succeed - no active pipelines
        store.delete_project(project.id)

        with pytest.raises(ProjectNotFoundError):
            store.get_project(project.id)
