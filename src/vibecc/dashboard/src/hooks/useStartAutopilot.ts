import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AutopilotAction } from "../types/api";

export function useStartAutopilot(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient.post<AutopilotAction>(
        `/projects/${projectId}/autopilot/start`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["autopilot", projectId] });
    },
  });
}
