import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { AutopilotStatus } from "../types/api";

export function useAutopilotStatus(projectId: string) {
  return useQuery({
    queryKey: ["autopilot", projectId],
    queryFn: () =>
      apiClient.get<AutopilotStatus>(`/projects/${projectId}/autopilot`),
    retry: false,
  });
}
