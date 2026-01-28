import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AutopilotAction } from "../types/api";

export function useStopAutopilot(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient.post<AutopilotAction>(
        `/projects/${projectId}/autopilot/stop`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["autopilot", projectId] });
    },
  });
}
