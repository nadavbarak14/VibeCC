import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { SyncResult } from "../types/api";

export function useSyncQueue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient.post<SyncResult>(`/projects/${projectId}/sync`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines", projectId] });
      queryClient.invalidateQueries({ queryKey: ["autopilot", projectId] });
    },
  });
}
