import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { Pipeline } from "../types/api";

export function usePipelines(projectId: string) {
  return useQuery({
    queryKey: ["pipelines", projectId],
    queryFn: () =>
      apiClient.get<Pipeline[]>(`/pipelines?project_id=${projectId}`),
  });
}
