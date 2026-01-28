import { useNavigate } from "react-router-dom";
import type { Project } from "../../types/api";
import { useAutopilotStatus } from "../../hooks/useAutopilotStatus";
import { Card } from "../common/Card";
import { Badge } from "../common/Badge";

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  const navigate = useNavigate();
  const { data: status } = useAutopilotStatus(project.id);

  const isRunning = status?.running ?? false;
  const activePipelines = status?.active_pipelines;

  return (
    <Card
      clickable
      onClick={() => navigate(`/projects/${project.id}`)}
      data-testid={`project-card-${project.id}`}
    >
      <div className="p-5">
        <div className="flex items-start justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            {project.name}
          </h3>
          {status ? (
            <Badge
              label={isRunning ? "Running" : "Stopped"}
              color={isRunning ? "green" : "gray"}
            />
          ) : (
            <Badge label="Unknown" color="gray" />
          )}
        </div>
        <p className="mt-1 text-sm text-gray-500">{project.repo}</p>
        <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
          <span>Branch: {project.base_branch}</span>
          {activePipelines !== undefined && (
            <span data-testid="pipeline-count">
              {activePipelines} active{" "}
              {activePipelines === 1 ? "pipeline" : "pipelines"}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
