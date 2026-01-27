# VibeCC - High Level Design

## Overview

VibeCC is a deterministic state machine that "compiles" GitHub tickets into merged code. It treats the SDLC as a compilation pipeline with strict inputs, transformation passes, and quality gates.

## System Diagram

```
                                    ┌─────────────────┐
                                    │    Dashboard    │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │    REST API     │
                                    └────────┬────────┘
                                             │
┌────────────────────────────────────────────┼────────────────────────────────────────────┐
│                                            │                                             │
│  ┌─────────────────┐              ┌────────▼────────┐              ┌─────────────────┐  │
│  │ Project Manager │◄────────────►│   Orchestrator  │◄────────────►│    Scheduler    │  │
│  └─────────────────┘              └────────┬────────┘              └─────────────────┘  │
│                                            │                                             │
│               ┌────────────────────────────┼────────────────────────────┐               │
│               │                            │                            │               │
│               ▼                            ▼                            ▼               │
│      ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐     │
│      │  Kanban Adapter │          │   State Store   │          │   Git Manager   │     │
│      └─────────────────┘          └─────────────────┘          └─────────────────┘     │
│                                                                                         │
│                              ┌──────────────────────────┐                              │
│                              │     Worker Pipeline      │                              │
│                              │                          │                              │
│                              │  ┌──────────────────┐    │                              │
│                              │  │   Coder Worker   │    │                              │
│                              │  └────────┬─────────┘    │                              │
│                              │           │              │                              │
│                              │  ┌────────▼─────────┐    │                              │
│                              │  │  Testing Runner  │    │                              │
│                              │  └────────┬─────────┘    │                              │
│                              │           │              │                              │
│                              │  ┌────────▼─────────┐    │                              │
│                              │  │ Reviewer Worker  │    │                              │
│                              │  └──────────────────┘    │                              │
│                              └──────────────────────────┘                              │
│                                                                                         │
│                                        VibeCC Server                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                    │                         │                         │
                    ▼                         ▼                         ▼
             ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
             │   GitHub    │           │ Claude Code │           │ Target Repo │
             │     API     │           │     CLI     │           │   (local)   │
             └─────────────┘           └─────────────┘           └─────────────┘
```

## Pipeline Flow

```
QUEUE → CODING → TESTING → REVIEW → MERGED
           │         │         │
           └────◄────┴────◄────┘  (retry on failure)
                     │
                  FAILED  (after max retries, stops autopilot)
```

## Proposed Components

| Component | Responsibility | External Dependencies |
|-----------|---------------|----------------------|
| **Orchestrator** | State machine - manages ticket transitions through pipeline | None |
| **Scheduler** | Decides when to pull tickets from queue based on capacity | None |
| **State Store** | Persists pipeline state (coding/testing/review, retries, feedback) | Database |
| **Kanban Adapter** | Abstracts ticket operations (GitHub Projects for now) | GitHub API |
| **Git Manager** | Branch, push, PR, merge operations | GitHub API, local git |
| **Coder Worker** | Invokes Claude Code CLI for coding | Claude Code CLI |
| **Testing Runner** | Push, create PR, wait for CI (no AI) | GitHub API |
| **Reviewer Worker** | Invokes Claude Code CLI for review | Claude Code CLI |
| **Project Manager** | Multi-project configuration and validation | None |
| **REST API** | HTTP interface for dashboard and external use | None |
| **Dashboard** | Web UI for monitoring and control | REST API |

## Component Dependencies

```
Dashboard
    └── REST API
            └── Orchestrator
                    ├── Scheduler
                    │       └── Kanban Adapter
                    ├── State Store
                    ├── Kanban Adapter
                    ├── Git Manager
                    ├── Coder Worker
                    │       └── Git Manager
                    ├── Testing Runner
                    │       └── Git Manager
                    └── Reviewer Worker
                            └── Git Manager

Project Manager
    └── State Store
```

## Documentation Structure

```
docs/
├── design/
│   ├── HIGH_LEVEL_DESIGN.md           # This file
│   │
│   └── components/
│       ├── orchestrator/
│       │   ├── DESIGN.md              # Detailed design, flows, edge cases
│       │   └── API.md                 # Full interface definition
│       │
│       ├── scheduler/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── state_store/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── kanban_adapter/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── git_manager/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── coder_worker/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── testing_runner/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── reviewer_worker/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── project_manager/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       ├── rest_api/
│       │   ├── DESIGN.md
│       │   └── API.md
│       │
│       └── dashboard/
│           ├── DESIGN.md
│           └── API.md
```

## Open Questions

1. **Coder completion signal** - How does Coder Worker know Claude Code finished?
2. **Prompt templates** - Where stored? Per project? Global?
3. **Error recovery** - What if VibeCC crashes mid-pipeline?
4. **Logging strategy** - Centralized? Per component?

## Next Steps

1. Review and approve component list
2. Create component folders with DESIGN.md and API.md
3. Create GitHub epics for parallel development
