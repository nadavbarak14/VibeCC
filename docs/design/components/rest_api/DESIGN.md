# REST API - Design

## Overview

REST API exposes State Store data and Orchestrator controls to the Dashboard and external clients. Built with FastAPI for async support and automatic OpenAPI documentation.

## Responsibilities

- Expose State Store data via HTTP endpoints
- Control Orchestrator (start/stop autopilot)
- Stream real-time updates via SSE
- Serve OpenAPI documentation

## Not Responsible For

- Business logic → Orchestrator
- Data persistence → State Store
- UI rendering → Dashboard

## Technology

### FastAPI

Chosen for:
- Async native (good for SSE, long operations)
- Automatic OpenAPI/Swagger docs
- Pydantic models for validation
- Modern Python with type hints

### SSE (Server-Sent Events)

Chosen over WebSocket because:
- Simpler implementation
- One-way push is sufficient (dashboard receives updates)
- Commands use regular HTTP POST (no bi-directional needed)
- Better browser support, auto-reconnect built-in

## Architecture

```
┌─────────────┐     HTTP      ┌─────────────┐
│  Dashboard  │◄─────────────►│  REST API   │
└─────────────┘               └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌───────────┐   ┌─────────────┐  ┌──────────────┐
             │   State   │   │Orchestrator │  │  SSE Event   │
             │   Store   │   │  (control)  │  │   Manager    │
             └───────────┘   └─────────────┘  └──────────────┘
```

## SSE Event Flow

```
1. Dashboard connects to /events/stream
2. REST API holds connection open
3. When Orchestrator updates state:
   - Orchestrator calls EventManager.emit(event)
   - EventManager pushes to all connected SSE clients
4. Dashboard receives event, updates UI
```

## File Structure

```
src/vibecc/api/
├── __init__.py
├── app.py              # FastAPI app setup
├── routes/
│   ├── __init__.py
│   ├── projects.py     # /projects endpoints
│   ├── pipelines.py    # /pipelines endpoints
│   ├── history.py      # /history endpoints
│   ├── control.py      # /control (start/stop) endpoints
│   └── events.py       # /events SSE stream
├── models.py           # Pydantic request/response models
├── events.py           # SSE event manager
└── dependencies.py     # FastAPI dependencies (StateStore, Orchestrator)
```

## Design Decisions

### Why separate routes files?
- Clear organization by resource
- Easier to test individual route groups
- Follows FastAPI best practices

### Why EventManager?
- Decouples Orchestrator from SSE implementation
- Allows multiple SSE connections
- Can buffer events if needed

### No authentication for MVP
- Simplifies initial development
- Can add later (API keys, OAuth)
- Assumes trusted network for now

## Error Handling

- Return appropriate HTTP status codes (404, 400, 500)
- Consistent error response format
- Log errors for debugging

## Configuration

```python
class APIConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
```
