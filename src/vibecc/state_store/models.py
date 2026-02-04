"""SQLAlchemy models for State Store."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime  # noqa: TC003 - used at runtime for SQLAlchemy
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class PipelineState(StrEnum):
    """Pipeline state enum."""

    QUEUED = "queued"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"
    MERGED = "merged"
    FAILED = "failed"


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Project(Base):
    """Project model - stores project configuration."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    base_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    github_project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_retries_ci: Mapped[int] = mapped_column(Integer, nullable=False)
    max_retries_review: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pipelines: Mapped[list[Pipeline]] = relationship(
        "Pipeline", back_populates="project", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        name: str,
        repo: str,
        id: str | None = None,
        base_branch: str = "main",
        github_project_id: int | None = None,
        max_retries_ci: int = 3,
        max_retries_review: int = 3,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.id = id if id is not None else generate_uuid()
        self.name = name
        self.repo = repo
        self.base_branch = base_branch
        self.github_project_id = github_project_id
        self.max_retries_ci = max_retries_ci
        self.max_retries_review = max_retries_review

    def __repr__(self) -> str:
        return f"<Project(id={self.id!r}, name={self.name!r}, repo={self.repo!r})>"


class Pipeline(Base):
    """Pipeline model - stores active pipeline state."""

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    ticket_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ticket_title: Mapped[str] = mapped_column(String(500), nullable=False)
    ticket_body: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pr_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count_ci: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_count_review: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="pipelines")

    def __init__(
        self,
        project_id: str,
        ticket_id: str,
        ticket_title: str,
        branch_name: str,
        id: str | None = None,
        ticket_body: str = "",
        state: str | None = None,
        pr_id: int | None = None,
        pr_url: str | None = None,
        retry_count_ci: int = 0,
        retry_count_review: int = 0,
        feedback: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.id = id if id is not None else generate_uuid()
        self.project_id = project_id
        self.ticket_id = ticket_id
        self.ticket_title = ticket_title
        self.ticket_body = ticket_body
        self.state = state if state is not None else PipelineState.QUEUED.value
        self.branch_name = branch_name
        self.pr_id = pr_id
        self.pr_url = pr_url
        self.retry_count_ci = retry_count_ci
        self.retry_count_review = retry_count_review
        self.feedback = feedback

    @property
    def pipeline_state(self) -> PipelineState:
        """Get state as PipelineState enum."""
        return PipelineState(self.state)

    @pipeline_state.setter
    def pipeline_state(self, value: PipelineState) -> None:
        """Set state from PipelineState enum."""
        self.state = value.value

    def __repr__(self) -> str:
        return f"<Pipeline(id={self.id!r}, ticket_id={self.ticket_id!r}, state={self.state!r})>"


class PipelineHistory(Base):
    """Pipeline history model - stores completed pipeline records."""

    __tablename__ = "pipeline_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ticket_id: Mapped[str] = mapped_column(String(50), nullable=False)
    ticket_title: Mapped[str] = mapped_column(String(500), nullable=False)
    final_state: Mapped[str] = mapped_column(String(20), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pr_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_retries_ci: Mapped[int] = mapped_column(Integer, nullable=False)
    total_retries_review: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    def __init__(
        self,
        project_id: str,
        ticket_id: str,
        ticket_title: str,
        final_state: str,
        branch_name: str,
        started_at: datetime,
        id: str | None = None,
        pr_id: int | None = None,
        pr_url: str | None = None,
        total_retries_ci: int = 0,
        total_retries_review: int = 0,
        duration_seconds: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.id = id if id is not None else generate_uuid()
        self.project_id = project_id
        self.ticket_id = ticket_id
        self.ticket_title = ticket_title
        self.final_state = final_state
        self.branch_name = branch_name
        self.started_at = started_at
        self.pr_id = pr_id
        self.pr_url = pr_url
        self.total_retries_ci = total_retries_ci
        self.total_retries_review = total_retries_review
        self.duration_seconds = duration_seconds

    @property
    def final_pipeline_state(self) -> PipelineState:
        """Get final_state as PipelineState enum."""
        return PipelineState(self.final_state)

    def __repr__(self) -> str:
        return (
            f"<PipelineHistory(id={self.id!r}, ticket_id={self.ticket_id!r}, "
            f"final_state={self.final_state!r})>"
        )


@dataclass
class HistoryStats:
    """Aggregated statistics from pipeline history."""

    total_completed: int
    total_merged: int
    total_failed: int
    avg_duration_seconds: float
    avg_retries_ci: float
    avg_retries_review: float
