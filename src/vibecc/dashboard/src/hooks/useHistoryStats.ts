import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { HistoryStats } from "../types/api";

export function useHistoryStats(projectId: string) {
  return useQuery({
    queryKey: ["history-stats", projectId],
    queryFn: () =>
      apiClient.get<HistoryStats>(
        `/history/stats?project_id=${projectId}`,
      ),
  });
}
