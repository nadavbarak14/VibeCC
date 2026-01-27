# Dashboard - Design

## Overview

Web-based dashboard for monitoring and controlling VibeCC. Jira-inspired kanban interface with real-time updates.

## Responsibilities

- Display projects and their status
- Visualize pipelines as kanban board
- Show pipeline details and live logs
- Control autopilot (start/stop)
- Display history and statistics

## Not Responsible For

- Business logic → Orchestrator
- Data persistence → State Store
- API → REST API

## Technology

### React
- Component-based architecture
- Good ecosystem for real-time UX
- Widely known, easy to maintain

### Tailwind CSS
- Utility-first, fast to style
- Clean, modern look
- No custom CSS needed for most things

### Additional Libraries
- **React Query** - Data fetching, caching, refetching
- **React Router** - Navigation
- **EventSource API** - SSE for real-time (native browser API)

## Views

### 1. Projects Home (`/`)
- Grid of project cards
- Each card: name, repo, status indicator, active pipeline count
- Click card → navigate to project board
- "Add Project" button

### 2. Project Board (`/projects/:id`)
- Kanban columns: Queue, Coding, Testing, Review, Done, Failed
- Cards move between columns in real-time
- Click card → open detail panel
- Header: project name, autopilot toggle, settings button

### 3. Pipeline Detail (slide-out panel)
- Ticket info (number, title, description)
- Current state with visual indicator
- Branch name, PR link (when available)
- Retry counts
- Timeline of state transitions
- Live log stream
- Feedback history (if retried)

### 4. History (`/projects/:id/history`)
- Table of completed pipelines
- Columns: ticket, status, duration, retries, completed at
- Filters: date range, final status
- Stats summary at top

### 5. Settings (modal or panel)
- Autopilot start/stop
- Max retries configuration
- Base branch (read-only for now)

## Component Structure

```
src/
├── components/
│   ├── Layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Layout.tsx
│   ├── Projects/
│   │   ├── ProjectCard.tsx
│   │   └── ProjectGrid.tsx
│   ├── Board/
│   │   ├── KanbanBoard.tsx
│   │   ├── KanbanColumn.tsx
│   │   └── PipelineCard.tsx
│   ├── Pipeline/
│   │   ├── PipelineDetail.tsx
│   │   ├── Timeline.tsx
│   │   └── LogStream.tsx
│   ├── History/
│   │   ├── HistoryTable.tsx
│   │   └── StatsBar.tsx
│   └── common/
│       ├── Button.tsx
│       ├── Card.tsx
│       ├── Badge.tsx
│       └── Modal.tsx
├── hooks/
│   ├── useProjects.ts
│   ├── usePipelines.ts
│   ├── useSSE.ts
│   └── useAutopilot.ts
├── pages/
│   ├── HomePage.tsx
│   ├── BoardPage.tsx
│   └── HistoryPage.tsx
├── api/
│   └── client.ts
└── App.tsx
```

## Real-time Updates

```
1. Dashboard connects to /api/v1/events/stream?project_id=xxx
2. useSSE hook manages EventSource connection
3. On event received:
   - pipeline_created → add card to Queue column
   - pipeline_updated → move card to new column with animation
   - pipeline_completed → move to Done or Failed
   - log → append to LogStream component
4. React Query cache invalidated on relevant events
```

## State Management

- **Server state** via React Query (projects, pipelines, history)
- **Local UI state** via React useState (selected pipeline, filters, modals)
- **No Redux** - not needed for this scope

## Design Tokens

```css
/* Colors */
--color-queue: #6B7280;      /* gray */
--color-coding: #3B82F6;     /* blue */
--color-testing: #F59E0B;    /* amber */
--color-review: #8B5CF6;     /* purple */
--color-done: #10B981;       /* green */
--color-failed: #EF4444;     /* red */
```

## File Location

```
src/vibecc/dashboard/
├── package.json
├── vite.config.ts
├── index.html
├── src/
│   └── ... (structure above)
└── public/
```

## Build & Serve

- Built with Vite
- Production build served by FastAPI (static files)
- Development: Vite dev server with proxy to API
