import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";
import type { Project } from "../types/api";

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.get<Project[]>("/projects"),
  });
}
