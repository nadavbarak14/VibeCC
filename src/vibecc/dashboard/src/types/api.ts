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

export type PipelineState =
  | "queued"
  | "coding"
  | "testing"
  | "review"
  | "merged"
  | "failed";

export interface Pipeline {
  id: string;
  project_id: string;
  ticket_id: string;
  ticket_title: string;
  ticket_body: string;
  state: PipelineState;
  branch_name: string;
  pr_id: number | null;
  pr_url: string | null;
  retry_count_ci: number;
  retry_count_review: number;
  feedback: string | null;
  created_at: string;
  updated_at: string;
}

export interface LogEntry {
  pipeline_id: string;
  level: string;
  message: string;
  timestamp: string;
}

export interface PipelineHistory {
  id: string;
  project_id: string;
  ticket_id: string;
  ticket_title: string;
  final_state: "merged" | "failed";
  branch_name: string;
  pr_id: number | null;
  pr_url: string | null;
  total_retries_ci: number;
  total_retries_review: number;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
}

export interface HistoryStats {
  total_completed: number;
  total_merged: number;
  total_failed: number;
  avg_duration_seconds: number;
  avg_retries_ci: number;
  avg_retries_review: number;
}

export interface HistoryFilters {
  final_state?: "merged" | "failed";
  limit?: number;
  offset?: number;
}
