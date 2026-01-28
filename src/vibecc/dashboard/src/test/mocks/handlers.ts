import { http, HttpResponse } from "msw";
import type { Project, AutopilotStatus, APIResponse } from "../../types/api";

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

export const handlers = [
  http.get("/api/v1/projects", () => {
    return HttpResponse.json({
      data: mockProjects,
      error: null,
    } satisfies APIResponse<Project[]>);
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
];
