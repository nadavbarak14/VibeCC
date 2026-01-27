# State Store - Design

## Overview

State Store is a pure storage component for pipeline state and project configuration. It provides simple CRUD operations with no business logic, events, or real-time features.

## Responsibilities

- Store and retrieve pipeline state
- Store and retrieve project configuration
- Store pipeline history (completed/failed)
- Persist to SQLite

## Not Responsible For

- Business logic (state transitions) → Orchestrator
- Logging steps/events → Orchestrator
- Real-time notifications → Orchestrator
- Validating state transitions → Orchestrator

## Data Model

### Project

```
Project
├── id: str (uuid)
├── name: str
├── repo: str (owner/repo)
├── base_branch: str (default: "main")
├── github_project_id: int (for kanban)
├── max_retries_ci: int
├── max_retries_review: int
├── created_at: datetime
└── updated_at: datetime
```

### Pipeline

Active ticket being processed.

```
Pipeline
├── id: str (uuid)
├── project_id: str (FK → Project)
├── ticket_id: str (GitHub issue number)
├── ticket_title: str
├── ticket_body: str
├── state: PipelineState (enum)
├── branch_name: str
├── pr_id: int (nullable, set after PR created)
├── pr_url: str (nullable)
├── retry_count_ci: int
├── retry_count_review: int
├── feedback: str (nullable, last failure feedback)
├── created_at: datetime
└── updated_at: datetime
```

### PipelineState (enum)

```
QUEUED      # Pulled from queue, branch being created
CODING      # Claude Code working
TESTING     # PR created, waiting for CI
REVIEW      # Claude Code reviewing
MERGED      # Successfully merged
FAILED      # Max retries exceeded, stopped
```

### PipelineHistory

Completed (merged or failed) pipelines for historical record.

```
PipelineHistory
├── id: str (uuid)
├── project_id: str
├── ticket_id: str
├── ticket_title: str
├── final_state: PipelineState (MERGED or FAILED)
├── branch_name: str
├── pr_id: int (nullable)
├── pr_url: str (nullable)
├── total_retries_ci: int
├── total_retries_review: int
├── started_at: datetime
├── completed_at: datetime
└── duration_seconds: int
```

## Database

- SQLite for simplicity
- Single file: `vibecc.db` (configurable path)
- Use SQLAlchemy for ORM
- Migrations via Alembic

## Design Decisions

### Why SQLite?
- Simple, no server needed
- Good enough for single-machine deployment
- Easy to backup (single file)
- Can migrate to PostgreSQL later if needed

### Why SQLAlchemy?
- Clean ORM, type hints support
- Easy to swap database backends
- Alembic integration for migrations

### Why separate Pipeline and PipelineHistory?
- Active pipelines queried frequently, should be small table
- History grows indefinitely, different query patterns
- Clear separation of concerns

## Error Handling

- State Store raises exceptions on errors (not found, constraint violations)
- Orchestrator handles exceptions and decides what to do
- No silent failures

## Thread Safety

- SQLite with WAL mode for concurrent reads
- Single writer assumed (Orchestrator is single point of control)
- If multiple Orchestrator instances needed later, switch to PostgreSQL

## File Location

```
src/vibecc/state_store/
├── __init__.py
├── models.py      # SQLAlchemy models
├── store.py       # StateStore class
└── migrations/    # Alembic migrations
```
