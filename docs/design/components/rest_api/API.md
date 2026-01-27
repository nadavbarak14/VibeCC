# REST API - Endpoints

## Base URL

```
http://localhost:8000/api/v1
```

## Response Format

All responses follow this structure:

```json
{
  "data": { ... },      // Response payload (or null on error)
  "error": null         // Error message (or null on success)
}
```

---

## Projects

### List Projects

```
GET /projects
```

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "My App",
      "repo": "owner/repo",
      "base_branch": "main",
      "github_project_id": 12345,
      "max_retries_ci": 3,
      "max_retries_review": 3,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "error": null
}
```

### Create Project

```
POST /projects
```

**Request:**
```json
{
  "name": "My App",
  "repo": "owner/repo",
  "base_branch": "main",
  "github_project_id": 12345,
  "max_retries_ci": 3,
  "max_retries_review": 3
}
```

**Response:** `201 Created`
```json
{
  "data": { "id": "uuid", ... },
  "error": null
}
```

### Get Project

```
GET /projects/{project_id}
```

**Response:** `200 OK` or `404 Not Found`

### Update Project

```
PATCH /projects/{project_id}
```

**Request:** (partial update, only include fields to change)
```json
{
  "max_retries_ci": 5
}
```

**Response:** `200 OK` or `404 Not Found`

### Delete Project

```
DELETE /projects/{project_id}
```

**Response:** `204 No Content`, `404 Not Found`, or `409 Conflict` (has active pipelines)

---

## Pipelines

### List Pipelines

```
GET /pipelines?project_id={uuid}&state={state}
```

**Query Parameters:**
- `project_id` (optional): Filter by project
- `state` (optional): Filter by state (queued, coding, testing, review, merged, failed)

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "project_id": "uuid",
      "ticket_id": "42",
      "ticket_title": "Add login feature",
      "ticket_body": "...",
      "state": "coding",
      "branch_name": "ticket-42",
      "pr_id": null,
      "pr_url": null,
      "retry_count_ci": 0,
      "retry_count_review": 0,
      "feedback": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "error": null
}
```

### Get Pipeline

```
GET /pipelines/{pipeline_id}
```

**Response:** `200 OK` or `404 Not Found`

### Get Pipeline by Ticket

```
GET /projects/{project_id}/tickets/{ticket_id}/pipeline
```

**Response:** `200 OK` or `404 Not Found`

---

## History

### List History

```
GET /history?project_id={uuid}&final_state={state}&limit={n}&offset={n}
```

**Query Parameters:**
- `project_id` (optional): Filter by project
- `final_state` (optional): Filter by final state (merged, failed)
- `limit` (optional, default 100): Max results
- `offset` (optional, default 0): Pagination offset

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "project_id": "uuid",
      "ticket_id": "42",
      "ticket_title": "Add login feature",
      "final_state": "merged",
      "branch_name": "ticket-42",
      "pr_id": 123,
      "pr_url": "https://github.com/...",
      "total_retries_ci": 1,
      "total_retries_review": 0,
      "started_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T01:00:00Z",
      "duration_seconds": 3600
    }
  ],
  "error": null
}
```

### Get History Stats

```
GET /history/stats?project_id={uuid}
```

**Response:**
```json
{
  "data": {
    "total_completed": 50,
    "total_merged": 45,
    "total_failed": 5,
    "avg_duration_seconds": 1800.5,
    "avg_retries_ci": 0.3,
    "avg_retries_review": 0.1
  },
  "error": null
}
```

---

## Control (Orchestrator)

### Get Autopilot Status

```
GET /projects/{project_id}/autopilot
```

**Response:**
```json
{
  "data": {
    "project_id": "uuid",
    "running": true,
    "active_pipelines": 2,
    "queued_tickets": 5
  },
  "error": null
}
```

### Start Autopilot

```
POST /projects/{project_id}/autopilot/start
```

**Response:** `200 OK`
```json
{
  "data": {
    "message": "Autopilot started"
  },
  "error": null
}
```

### Stop Autopilot

```
POST /projects/{project_id}/autopilot/stop
```

**Response:** `200 OK`
```json
{
  "data": {
    "message": "Autopilot stopped"
  },
  "error": null
}
```

---

## Events (SSE)

### Subscribe to Events

```
GET /events/stream?project_id={uuid}
```

**Query Parameters:**
- `project_id` (optional): Filter events by project (all projects if omitted)

**Response:** `text/event-stream`

Connection stays open. Server sends events as they occur:

```
event: pipeline_created
data: {"pipeline_id": "uuid", "project_id": "uuid", "ticket_id": "42", "state": "queued"}

event: pipeline_updated
data: {"pipeline_id": "uuid", "state": "coding", "previous_state": "queued"}

event: pipeline_completed
data: {"pipeline_id": "uuid", "final_state": "merged"}

event: autopilot_started
data: {"project_id": "uuid"}

event: autopilot_stopped
data: {"project_id": "uuid", "reason": "manual"}

event: log
data: {"pipeline_id": "uuid", "level": "info", "message": "Starting Claude Code...", "timestamp": "..."}
```

### Event Types

| Event | Description |
|-------|-------------|
| `pipeline_created` | New pipeline started |
| `pipeline_updated` | Pipeline state changed |
| `pipeline_completed` | Pipeline finished (merged or failed) |
| `autopilot_started` | Autopilot started for project |
| `autopilot_stopped` | Autopilot stopped for project |
| `log` | Log message from Orchestrator/workers |
| `heartbeat` | Keep-alive (every 30s) |

---

## Error Responses

### 400 Bad Request

```json
{
  "data": null,
  "error": "Invalid project_id format"
}
```

### 404 Not Found

```json
{
  "data": null,
  "error": "Project not found"
}
```

### 409 Conflict

```json
{
  "data": null,
  "error": "Cannot delete project with active pipelines"
}
```

### 500 Internal Server Error

```json
{
  "data": null,
  "error": "Internal server error"
}
```

---

## OpenAPI Documentation

Auto-generated Swagger UI available at:

```
http://localhost:8000/docs
```

ReDoc available at:

```
http://localhost:8000/redoc
```
