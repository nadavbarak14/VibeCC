"""Database connection manager for State Store."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from vibecc.state_store.models import Base

if TYPE_CHECKING:
    from sqlalchemy import Engine


class Database:
    """Database connection manager.

    Manages SQLite database connections with WAL mode enabled.
    """

    def __init__(self, db_path: str = "vibecc.db") -> None:
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory DB.
        """
        self.db_path = db_path
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    @property
    def engine(self) -> Engine:
        """Get or create the database engine."""
        if self._engine is None:
            # Create parent directory if it doesn't exist
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            # For in-memory databases, use StaticPool to share connection across threads
            # and allow cross-thread access (needed for testing with TestClient)
            if self.db_path == ":memory:":
                self._engine = create_engine(
                    "sqlite:///:memory:",
                    echo=False,
                    future=True,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                )
            else:
                self._engine = create_engine(
                    f"sqlite:///{self.db_path}",
                    echo=False,
                    future=True,
                )

            # Enable WAL mode for concurrent reads
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
                cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
            )
        return self._session_factory

    def create_tables(self) -> None:
        """Create all tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables. Use with caution!"""
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            A new SQLAlchemy session.
        """
        return self.session_factory()

    def is_wal_mode(self) -> bool:
        """Check if WAL mode is enabled.

        Returns:
            True if WAL mode is enabled.
        """
        with self.engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()
            return mode == "wal"

    def close(self) -> None:
        """Close the database connection."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
