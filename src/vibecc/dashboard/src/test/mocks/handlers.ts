import { http, HttpResponse } from "msw";
import type {
  Project,
  AutopilotStatus,
  AutopilotAction,
  Pipeline,
  PipelineHistory,
  HistoryStats,
  SyncResult,
  APIResponse,
} from "../../types/api";

export const mockProjects: Project[] = [
  {
    id: "proj-1",
    name: "Frontend App",
    repo: "acme/frontend",
    base_branch: "main",
    github_project_id: null,
    max_retries_ci: 3,
    max_retries_review: 3,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "proj-2",
    name: "Backend API",
    repo: "acme/backend",
    base_branch: "develop",
    github_project_id: 42,
    max_retries_ci: 2,
    max_retries_review: 2,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
];

export const mockAutopilotStatuses: Record<string, AutopilotStatus> = {
  "proj-1": {
    project_id: "proj-1",
    running: true,
    active_pipelines: 2,
    queued_tickets: 5,
  },
  "proj-2": {
    project_id: "proj-2",
    running: false,
    active_pipelines: 0,
    queued_tickets: 0,
  },
};

export const mockPipelines: Pipeline[] = [
  {
    id: "pipe-1",
    project_id: "proj-1",
    ticket_id: "101",
    ticket_title: "Add user login",
    ticket_body: "Implement login flow",
    state: "queued",
    branch_name: "ticket-101",
    pr_id: null,
    pr_url: null,
    retry_count_ci: 0,
    retry_count_review: 0,
    feedback: null,
    created_at: "2024-01-10T00:00:00Z",
    updated_at: "2024-01-10T00:00:00Z",
  },
  {
    id: "pipe-2",
    project_id: "proj-1",
    ticket_id: "102",
    ticket_title: "Fix navbar styling",
    ticket_body: "Navbar is broken on mobile",
    state: "coding",
    branch_name: "ticket-102",
    pr_id: null,
    pr_url: null,
    retry_count_ci: 0,
    retry_count_review: 0,
    feedback: null,
    created_at: "2024-01-10T01:00:00Z",
    updated_at: "2024-01-10T01:00:00Z",
  },
  {
    id: "pipe-3",
    project_id: "proj-1",
    ticket_id: "103",
    ticket_title: "Add unit tests",
    ticket_body: "Cover auth module",
    state: "testing",
    branch_name: "ticket-103",
    pr_id: 10,
    pr_url: "https://github.com/acme/frontend/pull/10",
    retry_count_ci: 1,
    retry_count_review: 0,
    feedback: null,
    created_at: "2024-01-10T02:00:00Z",
    updated_at: "2024-01-10T02:00:00Z",
  },
  {
    id: "pipe-4",
    project_id: "proj-1",
    ticket_id: "104",
    ticket_title: "Update README",
    ticket_body: "Add setup instructions",
    state: "merged",
    branch_name: "ticket-104",
    pr_id: 8,
    pr_url: "https://github.com/acme/frontend/pull/8",
    retry_count_ci: 0,
    retry_count_review: 0,
    feedback: null,
    created_at: "2024-01-09T00:00:00Z",
    updated_at: "2024-01-09T12:00:00Z",
  },
  {
    id: "pipe-5",
    project_id: "proj-1",
    ticket_id: "105",
    ticket_title: "Refactor database layer",
    ticket_body: "Improve query performance",
    state: "failed",
    branch_name: "ticket-105",
    pr_id: 9,
    pr_url: "https://github.com/acme/frontend/pull/9",
    retry_count_ci: 3,
    retry_count_review: 0,
    feedback: "CI failed after max retries",
    created_at: "2024-01-08T00:00:00Z",
    updated_at: "2024-01-09T00:00:00Z",
  },
  {
    id: "pipe-6",
    project_id: "proj-1",
    ticket_id: "106",
    ticket_title: "Add search feature",
    ticket_body: "Full-text search",
    state: "queued",
    branch_name: "ticket-106",
    pr_id: null,
    pr_url: null,
    retry_count_ci: 0,
    retry_count_review: 0,
    feedback: null,
    created_at: "2024-01-10T03:00:00Z",
    updated_at: "2024-01-10T03:00:00Z",
  },
];

export const mockHistory: PipelineHistory[] = [
  {
    id: "hist-1",
    project_id: "proj-1",
    ticket_id: "90",
    ticket_title: "Setup CI pipeline",
    final_state: "merged",
    branch_name: "ticket-90",
    pr_id: 5,
    pr_url: "https://github.com/acme/frontend/pull/5",
    total_retries_ci: 1,
    total_retries_review: 0,
    started_at: "2024-01-05T10:00:00Z",
    completed_at: "2024-01-05T11:30:00Z",
    duration_seconds: 5400,
  },
  {
    id: "hist-2",
    project_id: "proj-1",
    ticket_id: "91",
    ticket_title: "Add authentication",
    final_state: "merged",
    branch_name: "ticket-91",
    pr_id: 6,
    pr_url: "https://github.com/acme/frontend/pull/6",
    total_retries_ci: 0,
    total_retries_review: 1,
    started_at: "2024-01-06T09:00:00Z",
    completed_at: "2024-01-06T12:00:00Z",
    duration_seconds: 10800,
  },
  {
    id: "hist-3",
    project_id: "proj-1",
    ticket_id: "92",
    ticket_title: "Migrate database",
    final_state: "failed",
    branch_name: "ticket-92",
    pr_id: 7,
    pr_url: "https://github.com/acme/frontend/pull/7",
    total_retries_ci: 3,
    total_retries_review: 0,
    started_at: "2024-01-07T08:00:00Z",
    completed_at: "2024-01-07T10:00:00Z",
    duration_seconds: 7200,
  },
];

export const mockHistoryStats: HistoryStats = {
  total_completed: 3,
  total_merged: 2,
  total_failed: 1,
  avg_duration_seconds: 7800,
  avg_retries_ci: 1.3,
  avg_retries_review: 0.3,
};

export const handlers = [
  http.get("/api/v1/projects", () => {
    return HttpResponse.json({
      data: mockProjects,
      error: null,
    } satisfies APIResponse<Project[]>);
  }),

  http.get("/api/v1/projects/:projectId", ({ params }) => {
    const { projectId } = params;
    const project = mockProjects.find((p) => p.id === projectId);
    if (!project) {
      return HttpResponse.json(
        { data: null, error: "Project not found" } satisfies APIResponse<null>,
        { status: 404 },
      );
    }
    return HttpResponse.json({
      data: project,
      error: null,
    } satisfies APIResponse<Project>);
  }),

  http.get("/api/v1/projects/:projectId/autopilot", ({ params }) => {
    const { projectId } = params;
    const status = mockAutopilotStatuses[projectId as string];
    if (!status) {
      return HttpResponse.json(
        { data: null, error: "Project not found" } satisfies APIResponse<null>,
        { status: 404 },
      );
    }
    return HttpResponse.json({
      data: status,
      error: null,
    } satisfies APIResponse<AutopilotStatus>);
  }),

  http.get("/api/v1/pipelines", ({ request }) => {
    const url = new URL(request.url);
    const projectId = url.searchParams.get("project_id");
    const filtered = projectId
      ? mockPipelines.filter((p) => p.project_id === projectId)
      : mockPipelines;
    return HttpResponse.json({
      data: filtered,
      error: null,
    } satisfies APIResponse<Pipeline[]>);
  }),

  http.get("/api/v1/history", ({ request }) => {
    const url = new URL(request.url);
    const projectId = url.searchParams.get("project_id");
    const finalState = url.searchParams.get("final_state");
    let filtered = projectId
      ? mockHistory.filter((h) => h.project_id === projectId)
      : mockHistory;
    if (finalState) {
      filtered = filtered.filter((h) => h.final_state === finalState);
    }
    return HttpResponse.json({
      data: filtered,
      error: null,
    } satisfies APIResponse<PipelineHistory[]>);
  }),

  http.get("/api/v1/history/stats", ({ request }) => {
    const url = new URL(request.url);
    const projectId = url.searchParams.get("project_id");
    if (!projectId) {
      return HttpResponse.json(
        { data: null, error: "project_id required" } satisfies APIResponse<null>,
        { status: 400 },
      );
    }
    return HttpResponse.json({
      data: mockHistoryStats,
      error: null,
    } satisfies APIResponse<HistoryStats>);
  }),

  http.post("/api/v1/projects/:projectId/autopilot/start", ({ params }) => {
    const { projectId } = params;
    if (!mockAutopilotStatuses[projectId as string]) {
      return HttpResponse.json(
        { data: null, error: "Project not found" } satisfies APIResponse<null>,
        { status: 404 },
      );
    }
    mockAutopilotStatuses[projectId as string] = {
      ...mockAutopilotStatuses[projectId as string],
      running: true,
    };
    return HttpResponse.json({
      data: { message: "Autopilot started" },
      error: null,
    } satisfies APIResponse<AutopilotAction>);
  }),

  http.post("/api/v1/projects/:projectId/autopilot/stop", ({ params }) => {
    const { projectId } = params;
    if (!mockAutopilotStatuses[projectId as string]) {
      return HttpResponse.json(
        { data: null, error: "Project not found" } satisfies APIResponse<null>,
        { status: 404 },
      );
    }
    mockAutopilotStatuses[projectId as string] = {
      ...mockAutopilotStatuses[projectId as string],
      running: false,
    };
    return HttpResponse.json({
      data: { message: "Autopilot stopped" },
      error: null,
    } satisfies APIResponse<AutopilotAction>);
  }),

  http.post("/api/v1/projects/:projectId/sync", ({ params }) => {
    const { projectId } = params;
    const project = mockProjects.find((p) => p.id === projectId);
    if (!project) {
      return HttpResponse.json(
        { data: null, error: "Project not found" } satisfies APIResponse<null>,
        { status: 404 },
      );
    }
    // Simulate starting the first queued pipeline
    const queued = mockPipelines.filter(
      (p) => p.project_id === projectId && p.state === "queued",
    );
    const started = queued.slice(0, 1);
    const remaining = queued.length - started.length;
    return HttpResponse.json({
      data: { started, remaining },
      error: null,
    } satisfies APIResponse<SyncResult>);
  }),
];
