"""Unit tests for State Store models."""

from datetime import datetime

from vibecc.state_store.models import (
    Pipeline,
    PipelineHistory,
    PipelineState,
    Project,
)


class TestPipelineStateEnum:
    """Tests for PipelineState enum."""

    def test_pipeline_state_enum_values(self) -> None:
        """All states exist (QUEUED, CODING, TESTING, REVIEW, MERGED, FAILED)."""
        assert PipelineState.QUEUED.value == "queued"
        assert PipelineState.CODING.value == "coding"
        assert PipelineState.TESTING.value == "testing"
        assert PipelineState.REVIEW.value == "review"
        assert PipelineState.MERGED.value == "merged"
        assert PipelineState.FAILED.value == "failed"

    def test_pipeline_state_enum_count(self) -> None:
        """Exactly 6 states exist."""
        assert len(PipelineState) == 6

    def test_pipeline_state_is_string_enum(self) -> None:
        """PipelineState values are strings."""
        for state in PipelineState:
            assert isinstance(state.value, str)


class TestProjectModel:
    """Tests for Project model."""

    def test_project_model_required_fields(self) -> None:
        """Cannot create Project without name, repo."""
        # Project requires name and repo
        project = Project(name="Test", repo="owner/repo")
        assert project.name == "Test"
        assert project.repo == "owner/repo"

    def test_project_model_defaults(self) -> None:
        """base_branch defaults to 'main', retries default to 3."""
        project = Project(name="Test", repo="owner/repo")
        assert project.base_branch == "main"
        assert project.max_retries_ci == 3
        assert project.max_retries_review == 3

    def test_project_model_nullable_github_project_id(self) -> None:
        """github_project_id can be null."""
        project = Project(name="Test", repo="owner/repo")
        assert project.github_project_id is None

        project_with_id = Project(name="Test", repo="owner/repo", github_project_id=123)
        assert project_with_id.github_project_id == 123

    def test_project_model_repr(self) -> None:
        """Project has a useful repr."""
        project = Project(id="test-id", name="Test", repo="owner/repo")
        repr_str = repr(project)
        assert "test-id" in repr_str
        assert "Test" in repr_str
        assert "owner/repo" in repr_str


class TestPipelineModel:
    """Tests for Pipeline model."""

    def test_pipeline_model_required_fields(self) -> None:
        """Pipeline has required fields."""
        pipeline = Pipeline(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        assert pipeline.project_id == "proj-1"
        assert pipeline.ticket_id == "42"
        assert pipeline.ticket_title == "Test ticket"
        assert pipeline.branch_name == "ticket-42"

    def test_pipeline_model_initial_state(self) -> None:
        """New pipeline starts in QUEUED state."""
        pipeline = Pipeline(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        assert pipeline.state == PipelineState.QUEUED.value

    def test_pipeline_model_nullable_fields(self) -> None:
        """pr_id, pr_url, feedback can be null."""
        pipeline = Pipeline(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        assert pipeline.pr_id is None
        assert pipeline.pr_url is None
        assert pipeline.feedback is None

    def test_pipeline_model_retry_defaults(self) -> None:
        """Retry counts default to 0."""
        pipeline = Pipeline(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        assert pipeline.retry_count_ci == 0
        assert pipeline.retry_count_review == 0

    def test_pipeline_state_property(self) -> None:
        """pipeline_state property converts to/from enum."""
        pipeline = Pipeline(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        assert pipeline.pipeline_state == PipelineState.QUEUED

        pipeline.pipeline_state = PipelineState.CODING
        assert pipeline.state == "coding"
        assert pipeline.pipeline_state == PipelineState.CODING

    def test_pipeline_model_repr(self) -> None:
        """Pipeline has a useful repr."""
        pipeline = Pipeline(
            id="pipe-1",
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            branch_name="ticket-42",
        )
        repr_str = repr(pipeline)
        assert "pipe-1" in repr_str
        assert "42" in repr_str
        assert "queued" in repr_str


class TestPipelineHistoryModel:
    """Tests for PipelineHistory model."""

    def test_pipeline_history_model_fields(self) -> None:
        """All fields map correctly from Pipeline."""
        history = PipelineHistory(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            final_state=PipelineState.MERGED.value,
            branch_name="ticket-42",
            pr_id=123,
            pr_url="https://github.com/owner/repo/pull/123",
            total_retries_ci=1,
            total_retries_review=0,
            started_at=datetime(2024, 1, 1, 10, 0),
            duration_seconds=3600,
        )

        assert history.project_id == "proj-1"
        assert history.ticket_id == "42"
        assert history.ticket_title == "Test ticket"
        assert history.final_state == "merged"
        assert history.branch_name == "ticket-42"
        assert history.pr_id == 123
        assert history.pr_url == "https://github.com/owner/repo/pull/123"
        assert history.total_retries_ci == 1
        assert history.total_retries_review == 0
        assert history.duration_seconds == 3600

    def test_pipeline_history_nullable_pr_fields(self) -> None:
        """pr_id and pr_url can be null (for failed before PR)."""
        history = PipelineHistory(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            final_state=PipelineState.FAILED.value,
            branch_name="ticket-42",
            started_at=datetime(2024, 1, 1, 10, 0),
        )
        assert history.pr_id is None
        assert history.pr_url is None

    def test_pipeline_history_final_state_property(self) -> None:
        """final_pipeline_state property converts to enum."""
        history = PipelineHistory(
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            final_state=PipelineState.MERGED.value,
            branch_name="ticket-42",
            started_at=datetime(2024, 1, 1, 10, 0),
        )
        assert history.final_pipeline_state == PipelineState.MERGED

    def test_pipeline_history_model_repr(self) -> None:
        """PipelineHistory has a useful repr."""
        history = PipelineHistory(
            id="hist-1",
            project_id="proj-1",
            ticket_id="42",
            ticket_title="Test ticket",
            final_state=PipelineState.MERGED.value,
            branch_name="ticket-42",
            started_at=datetime(2024, 1, 1, 10, 0),
        )
        repr_str = repr(history)
        assert "hist-1" in repr_str
        assert "42" in repr_str
        assert "merged" in repr_str
