export interface APIResponse<T> {
  data: T | null;
  error: string | null;
}

export interface Project {
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

export interface AutopilotStatus {
  project_id: string;
  running: boolean;
  active_pipelines: number;
  queued_tickets: number;
}
