import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { PipelineHistory, HistoryFilters } from "../types/api";

export function useHistory(projectId: string, filters?: HistoryFilters) {
  const params = new URLSearchParams({ project_id: projectId });
  if (filters?.final_state) {
    params.set("final_state", filters.final_state);
  }
  if (filters?.limit != null) {
    params.set("limit", String(filters.limit));
  }
  if (filters?.offset != null) {
    params.set("offset", String(filters.offset));
  }

  return useQuery({
    queryKey: ["history", projectId, filters],
    queryFn: () =>
      apiClient.get<PipelineHistory[]>(`/history?${params.toString()}`),
  });
}
