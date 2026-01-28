"""Integration tests for StateStore project operations."""

import tempfile
import threading
from pathlib import Path

import pytest

from vibecc.state_store import ProjectNotFoundError, StateStore


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def store(temp_db_path: str) -> StateStore:
    """Create a StateStore with a temporary database."""
    s = StateStore(temp_db_path)
    yield s
    s.close()
    # Cleanup
    Path(temp_db_path).unlink(missing_ok=True)
    Path(f"{temp_db_path}-wal").unlink(missing_ok=True)
    Path(f"{temp_db_path}-shm").unlink(missing_ok=True)


@pytest.mark.integration
class TestProjectPersistence:
    """Tests for project persistence."""

    def test_project_persists_across_reconnect(self, temp_db_path: str) -> None:
        """Create project, reconnect to DB, project still exists."""
        # Create project with first connection
        store1 = StateStore(temp_db_path)
        project = store1.create_project(name="Persistent", repo="owner/persistent")
        project_id = project.id
        store1.close()

        # Reconnect and verify
        store2 = StateStore(temp_db_path)
        retrieved = store2.get_project(project_id)
        store2.close()

        assert retrieved.id == project_id
        assert retrieved.name == "Persistent"
        assert retrieved.repo == "owner/persistent"

        # Cleanup
        Path(temp_db_path).unlink(missing_ok=True)
        Path(f"{temp_db_path}-wal").unlink(missing_ok=True)
        Path(f"{temp_db_path}-shm").unlink(missing_ok=True)


@pytest.mark.integration
class TestProjectCrudLifecycle:
    """Tests for full CRUD lifecycle."""

    def test_project_crud_full_lifecycle(self, store: StateStore) -> None:
        """Create -> Read -> Update -> Delete flow."""
        # Create
        project = store.create_project(
            name="Lifecycle Test",
            repo="owner/lifecycle",
            base_branch="main",
        )
        assert project.id is not None
        project_id = project.id

        # Read
        retrieved = store.get_project(project_id)
        assert retrieved.name == "Lifecycle Test"

        # Update
        updated = store.update_project(
            project_id,
            name="Updated Name",
            base_branch="develop",
        )
        assert updated.name == "Updated Name"
        assert updated.base_branch == "develop"

        # Verify update persisted
        re_retrieved = store.get_project(project_id)
        assert re_retrieved.name == "Updated Name"
        assert re_retrieved.base_branch == "develop"

        # Delete
        store.delete_project(project_id)

        # Verify deleted
        with pytest.raises(ProjectNotFoundError):
            store.get_project(project_id)


@pytest.mark.integration
class TestConcurrentProjectCreation:
    """Tests for concurrent operations."""

    def test_concurrent_project_creation(self, temp_db_path: str) -> None:
        """Two projects created without conflict."""
        # Pre-create the database and tables to avoid race condition in DDL
        initial_store = StateStore(temp_db_path)
        initial_store.close()

        results: list[str | Exception] = []
        errors: list[Exception] = []

        def create_project(name: str, repo: str) -> None:
            try:
                # Each thread gets its own connection
                store = StateStore(temp_db_path)
                project = store.create_project(name=name, repo=repo)
                results.append(project.id)
                store.close()
            except Exception as e:
                errors.append(e)

        # Create two projects concurrently
        thread1 = threading.Thread(target=create_project, args=("Project A", "owner/repo-a"))
        thread2 = threading.Thread(target=create_project, args=("Project B", "owner/repo-b"))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Both should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 2

        # Verify both projects exist
        store = StateStore(temp_db_path)
        projects = store.list_projects()
        store.close()

        assert len(projects) == 2
        names = {p.name for p in projects}
        assert names == {"Project A", "Project B"}

        # Cleanup
        Path(temp_db_path).unlink(missing_ok=True)
        Path(f"{temp_db_path}-wal").unlink(missing_ok=True)
        Path(f"{temp_db_path}-shm").unlink(missing_ok=True)
