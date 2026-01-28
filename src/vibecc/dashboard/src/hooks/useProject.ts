import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { Project } from "../types/api";

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => apiClient.get<Project>(`/projects/${projectId}`),
  });
}
