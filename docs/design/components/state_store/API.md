# State Store - API

## Overview

State Store exposes a Python class with methods for CRUD operations. Only Orchestrator should use this API.

## Class: StateStore

### Constructor

```python
def __init__(self, db_path: str = "vibecc.db") -> None:
    """
    Initialize State Store with SQLite database.
    Creates database and tables if they don't exist.

    Args:
        db_path: Path to SQLite database file
    """
```

---

## Project Operations

### create_project

```python
def create_project(
    self,
    name: str,
    repo: str,
    base_branch: str = "main",
    github_project_id: int | None = None,
    max_retries_ci: int = 3,
    max_retries_review: int = 3,
) -> Project:
    """
    Create a new project.

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
```

### get_project

```python
def get_project(self, project_id: str) -> Project:
    """
    Get project by ID.

    Raises:
        ProjectNotFoundError: If project doesn't exist
    """
```

### get_project_by_repo

```python
def get_project_by_repo(self, repo: str) -> Project:
    """
    Get project by repo name.

    Raises:
        ProjectNotFoundError: If project doesn't exist
    """
```

### list_projects

```python
def list_projects(self) -> list[Project]:
    """
    List all projects.

    Returns:
        List of all projects, ordered by name
    """
```

### update_project

```python
def update_project(
    self,
    project_id: str,
    name: str | None = None,
    base_branch: str | None = None,
    github_project_id: int | None = None,
    max_retries_ci: int | None = None,
    max_retries_review: int | None = None,
) -> Project:
    """
    Update project fields. Only provided fields are updated.

    Raises:
        ProjectNotFoundError: If project doesn't exist
    """
```

### delete_project

```python
def delete_project(self, project_id: str) -> None:
    """
    Delete a project. Fails if project has active pipelines.

    Raises:
        ProjectNotFoundError: If project doesn't exist
        ProjectHasActivePipelinesError: If project has active pipelines
    """
```

---

## Pipeline Operations

### create_pipeline

```python
def create_pipeline(
    self,
    project_id: str,
    ticket_id: str,
    ticket_title: str,
    ticket_body: str,
    branch_name: str,
) -> Pipeline:
    """
    Create a new pipeline for a ticket. Initial state is QUEUED.

    Args:
        project_id: Parent project ID
        ticket_id: GitHub issue number (as string)
        ticket_title: Issue title
        ticket_body: Issue body/description
        branch_name: Git branch name for this ticket

    Returns:
        Created Pipeline object

    Raises:
        ProjectNotFoundError: If project doesn't exist
        PipelineExistsError: If pipeline for this ticket already exists
    """
```

### get_pipeline

```python
def get_pipeline(self, pipeline_id: str) -> Pipeline:
    """
    Get pipeline by ID.

    Raises:
        PipelineNotFoundError: If pipeline doesn't exist
    """
```

### get_pipeline_by_ticket

```python
def get_pipeline_by_ticket(self, project_id: str, ticket_id: str) -> Pipeline:
    """
    Get pipeline by project and ticket ID.

    Raises:
        PipelineNotFoundError: If pipeline doesn't exist
    """
```

### list_pipelines

```python
def list_pipelines(
    self,
    project_id: str | None = None,
    state: PipelineState | None = None,
) -> list[Pipeline]:
    """
    List pipelines with optional filters.

    Args:
        project_id: Filter by project (None = all projects)
        state: Filter by state (None = all states)

    Returns:
        List of pipelines, ordered by created_at desc
    """
```

### update_pipeline

```python
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
    """
    Update pipeline fields. Only provided fields are updated.

    Note: This does NOT validate state transitions.
    Orchestrator is responsible for valid transitions.

    Raises:
        PipelineNotFoundError: If pipeline doesn't exist
    """
```

### delete_pipeline

```python
def delete_pipeline(self, pipeline_id: str) -> None:
    """
    Delete a pipeline (used after moving to history).

    Raises:
        PipelineNotFoundError: If pipeline doesn't exist
    """
```

---

## History Operations

### save_to_history

```python
def save_to_history(self, pipeline: Pipeline) -> PipelineHistory:
    """
    Move completed pipeline to history.

    Copies pipeline data to history table with completion timestamp.
    Does NOT delete the original pipeline (caller should do that).

    Args:
        pipeline: The completed pipeline (state should be MERGED or FAILED)

    Returns:
        Created PipelineHistory object
    """
```

### get_history

```python
def get_history(
    self,
    project_id: str | None = None,
    final_state: PipelineState | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PipelineHistory]:
    """
    Query pipeline history.

    Args:
        project_id: Filter by project (None = all)
        final_state: Filter by final state (None = all)
        limit: Max results to return
        offset: Offset for pagination

    Returns:
        List of historical pipelines, ordered by completed_at desc
    """
```

### get_history_stats

```python
def get_history_stats(
    self,
    project_id: str | None = None,
) -> HistoryStats:
    """
    Get aggregated stats from history.

    Returns:
        HistoryStats with counts, averages, etc.
    """
```

---

## Data Types

### Project

```python
@dataclass
class Project:
    id: str
    name: str
    repo: str
    base_branch: str
    github_project_id: int | None
    max_retries_ci: int
    max_retries_review: int
    created_at: datetime
    updated_at: datetime
```

### Pipeline

```python
@dataclass
class Pipeline:
    id: str
    project_id: str
    ticket_id: str
    ticket_title: str
    ticket_body: str
    state: PipelineState
    branch_name: str
    pr_id: int | None
    pr_url: str | None
    retry_count_ci: int
    retry_count_review: int
    feedback: str | None
    created_at: datetime
    updated_at: datetime
```

### PipelineState

```python
class PipelineState(Enum):
    QUEUED = "queued"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"
    MERGED = "merged"
    FAILED = "failed"
```

### PipelineHistory

```python
@dataclass
class PipelineHistory:
    id: str
    project_id: str
    ticket_id: str
    ticket_title: str
    final_state: PipelineState
    branch_name: str
    pr_id: int | None
    pr_url: str | None
    total_retries_ci: int
    total_retries_review: int
    started_at: datetime
    completed_at: datetime
    duration_seconds: int
```

### HistoryStats

```python
@dataclass
class HistoryStats:
    total_completed: int
    total_merged: int
    total_failed: int
    avg_duration_seconds: float
    avg_retries_ci: float
    avg_retries_review: float
```

---

## Exceptions

```python
class StateStoreError(Exception):
    """Base exception for State Store errors."""

class ProjectNotFoundError(StateStoreError):
    """Project with given ID does not exist."""

class ProjectExistsError(StateStoreError):
    """Project with given repo already exists."""

class ProjectHasActivePipelinesError(StateStoreError):
    """Cannot delete project with active pipelines."""

class PipelineNotFoundError(StateStoreError):
    """Pipeline with given ID does not exist."""

class PipelineExistsError(StateStoreError):
    """Pipeline for this ticket already exists."""
```

---

## Usage Example

```python
from vibecc.state_store import StateStore, PipelineState

# Initialize
store = StateStore("vibecc.db")

# Create project
project = store.create_project(
    name="My App",
    repo="myorg/myapp",
    base_branch="main",
)

# Create pipeline when ticket starts
pipeline = store.create_pipeline(
    project_id=project.id,
    ticket_id="42",
    ticket_title="Add login feature",
    ticket_body="Implement user login with OAuth",
    branch_name="ticket-42",
)

# Update state as pipeline progresses
store.update_pipeline(pipeline.id, state=PipelineState.CODING)
store.update_pipeline(pipeline.id, state=PipelineState.TESTING, pr_id=123)
store.update_pipeline(pipeline.id, state=PipelineState.REVIEW)
store.update_pipeline(pipeline.id, state=PipelineState.MERGED)

# Move to history and cleanup
store.save_to_history(pipeline)
store.delete_pipeline(pipeline.id)
```
