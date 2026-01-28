"""Integration tests for State Store database."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

from vibecc.state_store.database import Database
from vibecc.state_store.models import (
    Pipeline,
    PipelineHistory,
    PipelineState,
    Project,
)


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


@pytest.fixture
def database(temp_db_path: str) -> Database:
    """Create a database instance with tables."""
    db = Database(temp_db_path)
    db.create_tables()
    yield db
    db.close()
    # Cleanup
    Path(temp_db_path).unlink(missing_ok=True)
    Path(f"{temp_db_path}-wal").unlink(missing_ok=True)
    Path(f"{temp_db_path}-shm").unlink(missing_ok=True)


@pytest.mark.integration
class TestDatabaseSetup:
    """Tests for database setup."""

    def test_database_creates_file(self, temp_db_path: str) -> None:
        """SQLite file created at specified path."""
        db = Database(temp_db_path)
        db.create_tables()
        assert Path(temp_db_path).exists()
        db.close()

    def test_database_creates_tables(self, database: Database) -> None:
        """All three tables exist after init."""
        inspector = inspect(database.engine)
        tables = inspector.get_table_names()
        assert "projects" in tables
        assert "pipelines" in tables
        assert "pipeline_history" in tables

    def test_database_wal_mode(self, database: Database) -> None:
        """WAL mode is enabled."""
        assert database.is_wal_mode()

    def test_database_foreign_keys_enabled(self, database: Database) -> None:
        """Foreign keys are enabled."""
        with database.engine.connect() as conn:
            result = conn.execute(text("PRAGMA foreign_keys"))
            fk_enabled = result.scalar()
            assert fk_enabled == 1


@pytest.mark.integration
class TestMigrations:
    """Tests for database migrations."""

    def test_migrations_apply_cleanly(self, temp_db_path: str) -> None:
        """Tables can be created on fresh database."""
        db = Database(temp_db_path)
        # Should not raise
        db.create_tables()
        inspector = inspect(db.engine)
        assert len(inspector.get_table_names()) == 3
        db.close()


@pytest.mark.integration
class TestModelRoundtrip:
    """Tests for model persistence."""

    def test_model_roundtrip_project(self, database: Database) -> None:
        """Can insert and retrieve Project."""
        session = database.get_session()

        # Create
        project = Project(name="Test Project", repo="owner/repo")
        session.add(project)
        session.commit()
        project_id = project.id

        # Retrieve
        session.expunge_all()
        retrieved = session.get(Project, project_id)

        assert retrieved is not None
        assert retrieved.name == "Test Project"
        assert retrieved.repo == "owner/repo"
        assert retrieved.base_branch == "main"
        session.close()

    def test_model_roundtrip_pipeline(self, database: Database) -> None:
        """Can insert and retrieve Pipeline."""
        session = database.get_session()

        # Create project first (foreign key)
        project = Project(name="Test Project", repo="owner/repo")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

        # Create pipeline
        pipeline = Pipeline(
            project_id=project_id,
            ticket_id="42",
            ticket_title="Test ticket",
            ticket_body="Test body",
            branch_name="ticket-42",
        )
        session.add(pipeline)
        session.commit()
        pipeline_id = pipeline.id

        # Retrieve
        session.expunge_all()
        retrieved = session.get(Pipeline, pipeline_id)

        assert retrieved is not None
        assert retrieved.ticket_id == "42"
        assert retrieved.ticket_title == "Test ticket"
        assert retrieved.state == PipelineState.QUEUED.value
        session.close()

    def test_model_roundtrip_history(self, database: Database) -> None:
        """Can insert and retrieve PipelineHistory."""
        session = database.get_session()

        # Create history
        history = PipelineHistory(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            final_state=PipelineState.MERGED.value,
            branch_name="ticket-42",
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            total_retries_ci=0,
            total_retries_review=0,
            started_at=datetime(2024, 1, 1, 10, 0),
            duration_seconds=3600,
        )
        session.add(history)
        session.commit()
        history_id = history.id

        # Retrieve
        session.expunge_all()
        retrieved = session.get(PipelineHistory, history_id)

        assert retrieved is not None
        assert retrieved.ticket_id == "42"
        assert retrieved.final_state == PipelineState.MERGED.value
        assert retrieved.duration_seconds == 3600
        session.close()


@pytest.mark.integration
class TestForeignKeys:
    """Tests for foreign key relationships."""

    def test_foreign_key_project_pipeline(self, database: Database) -> None:
        """Pipeline references valid Project."""
        session = database.get_session()

        # Create project
        project = Project(name="Test Project", repo="owner/repo")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

        # Create pipeline with valid project_id
        pipeline = Pipeline(
            project_id=project_id,
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        session.add(pipeline)
        session.commit()

        # Verify relationship
        session.refresh(pipeline)
        assert pipeline.project is not None
        assert pipeline.project.id == project.id
        assert pipeline.project.name == "Test Project"
        session.close()

    def test_foreign_key_cascade_delete(self, database: Database) -> None:
        """Deleting project cascades to pipelines."""
        session = database.get_session()

        # Create project and pipeline
        project = Project(name="Test Project", repo="owner/repo")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

        pipeline = Pipeline(
            project_id=project_id,
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        session.add(pipeline)
        session.commit()
        pipeline_id = pipeline.id

        # Delete project
        session.delete(project)
        session.commit()

        # Pipeline should be deleted too
        assert session.get(Pipeline, pipeline_id) is None
        session.close()


@pytest.mark.integration
class TestTimestamps:
    """Tests for automatic timestamps."""

    def test_timestamps_auto_set(self, database: Database) -> None:
        """created_at and updated_at populated automatically."""
        session = database.get_session()

        # Create project
        before = datetime.now()
        project = Project(name="Test Project", repo="owner/repo")
        session.add(project)
        session.commit()
        after = datetime.now()

        session.refresh(project)
        assert project.created_at is not None
        assert project.updated_at is not None

        # Timestamps should be within reasonable range
        # Allow 1 second tolerance for test execution time
        assert project.created_at >= before - timedelta(seconds=1)
        assert project.created_at <= after + timedelta(seconds=1)
        session.close()


@pytest.mark.integration
class TestInMemoryDatabase:
    """Tests for in-memory database."""

    def test_in_memory_database(self) -> None:
        """In-memory database works correctly."""
        db = Database(":memory:")
        db.create_tables()

        session = db.get_session()
        project = Project(name="Test", repo="owner/repo")
        session.add(project)
        session.commit()

        # Verify
        projects = session.query(Project).all()
        assert len(projects) == 1
        assert projects[0].name == "Test"

        session.close()
        db.close()
