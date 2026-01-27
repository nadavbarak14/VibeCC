# Dashboard - API (Consumed)

## Overview

Dashboard consumes the REST API. This documents what endpoints each view uses.

## API Client

Base configuration:

```typescript
const API_BASE = '/api/v1';

// All requests use this client
const api = {
  get: (path) => fetch(`${API_BASE}${path}`).then(r => r.json()),
  post: (path, body) => fetch(`${API_BASE}${path}`, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => fetch(`${API_BASE}${path}`, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => fetch(`${API_BASE}${path}`, { method: 'DELETE' }),
};
```

---

## Projects Home

### Data Needed
- List of all projects with basic info

### Endpoints Used
```
GET /projects
```

### React Query Hook
```typescript
function useProjects() {
  return useQuery(['projects'], () => api.get('/projects'));
}
```

---

## Project Board

### Data Needed
- Project details
- All pipelines for project (grouped by state)
- Autopilot status

### Endpoints Used
```
GET /projects/{project_id}
GET /pipelines?project_id={project_id}
GET /projects/{project_id}/autopilot
```

### React Query Hooks
```typescript
function useProject(projectId: string) {
  return useQuery(['project', projectId], () => api.get(`/projects/${projectId}`));
}

function usePipelines(projectId: string) {
  return useQuery(['pipelines', projectId], () => api.get(`/pipelines?project_id=${projectId}`));
}

function useAutopilotStatus(projectId: string) {
  return useQuery(['autopilot', projectId], () => api.get(`/projects/${projectId}/autopilot`));
}
```

---

## Pipeline Detail

### Data Needed
- Full pipeline data (already have from board query)
- Live logs (via SSE)

### Endpoints Used
```
GET /pipelines/{pipeline_id}  (if not cached)
GET /events/stream?project_id={project_id}  (SSE for logs)
```

---

## History

### Data Needed
- List of historical pipelines
- Aggregated stats

### Endpoints Used
```
GET /history?project_id={project_id}&limit=50&offset=0
GET /history/stats?project_id={project_id}
```

### React Query Hooks
```typescript
function useHistory(projectId: string, filters: HistoryFilters) {
  return useQuery(
    ['history', projectId, filters],
    () => api.get(`/history?project_id=${projectId}&limit=${filters.limit}&offset=${filters.offset}`)
  );
}

function useHistoryStats(projectId: string) {
  return useQuery(['history-stats', projectId], () => api.get(`/history/stats?project_id=${projectId}`));
}
```

---

## Control Actions

### Start Autopilot
```typescript
function useStartAutopilot() {
  const queryClient = useQueryClient();
  return useMutation(
    (projectId: string) => api.post(`/projects/${projectId}/autopilot/start`),
    { onSuccess: () => queryClient.invalidateQueries(['autopilot']) }
  );
}
```

### Stop Autopilot
```typescript
function useStopAutopilot() {
  const queryClient = useQueryClient();
  return useMutation(
    (projectId: string) => api.post(`/projects/${projectId}/autopilot/stop`),
    { onSuccess: () => queryClient.invalidateQueries(['autopilot']) }
  );
}
```

---

## SSE Integration

### Hook
```typescript
function useSSE(projectId: string, onEvent: (event: SSEEvent) => void) {
  useEffect(() => {
    const eventSource = new EventSource(`/api/v1/events/stream?project_id=${projectId}`);

    eventSource.addEventListener('pipeline_created', (e) => {
      onEvent({ type: 'pipeline_created', data: JSON.parse(e.data) });
    });

    eventSource.addEventListener('pipeline_updated', (e) => {
      onEvent({ type: 'pipeline_updated', data: JSON.parse(e.data) });
    });

    eventSource.addEventListener('pipeline_completed', (e) => {
      onEvent({ type: 'pipeline_completed', data: JSON.parse(e.data) });
    });

    eventSource.addEventListener('log', (e) => {
      onEvent({ type: 'log', data: JSON.parse(e.data) });
    });

    return () => eventSource.close();
  }, [projectId, onEvent]);
}
```

### Cache Invalidation on Events
```typescript
// In BoardPage.tsx
const queryClient = useQueryClient();

useSSE(projectId, (event) => {
  if (event.type === 'pipeline_created' || event.type === 'pipeline_updated' || event.type === 'pipeline_completed') {
    queryClient.invalidateQueries(['pipelines', projectId]);
  }
});
```

---

## TypeScript Types

```typescript
interface Project {
  id: string;
  name: string;
  repo: string;
  base_branch: string;
  github_project_id: number | null;
  max_retries_ci: number;
  max_retries_review: number;
  created_at: string;
  updated_at: string;
}

interface Pipeline {
  id: string;
  project_id: string;
  ticket_id: string;
  ticket_title: string;
  ticket_body: string;
  state: 'queued' | 'coding' | 'testing' | 'review' | 'merged' | 'failed';
  branch_name: string;
  pr_id: number | null;
  pr_url: string | null;
  retry_count_ci: number;
  retry_count_review: number;
  feedback: string | null;
  created_at: string;
  updated_at: string;
}

interface PipelineHistory {
  id: string;
  project_id: string;
  ticket_id: string;
  ticket_title: string;
  final_state: 'merged' | 'failed';
  branch_name: string;
  pr_id: number | null;
  pr_url: string | null;
  total_retries_ci: number;
  total_retries_review: number;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
}

interface HistoryStats {
  total_completed: number;
  total_merged: number;
  total_failed: number;
  avg_duration_seconds: number;
  avg_retries_ci: number;
  avg_retries_review: number;
}

interface AutopilotStatus {
  project_id: string;
  running: boolean;
  active_pipelines: number;
  queued_tickets: number;
}

interface SSEEvent {
  type: 'pipeline_created' | 'pipeline_updated' | 'pipeline_completed' | 'log' | 'heartbeat';
  data: any;
}
```
