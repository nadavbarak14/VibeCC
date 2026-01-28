import { Link } from "react-router-dom";
import type { Project, AutopilotStatus } from "../../types/api";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";

interface BoardHeaderProps {
  project: Project;
  status?: AutopilotStatus;
}

export function BoardHeader({ project, status }: BoardHeaderProps) {
  const isRunning = status?.running ?? false;

  return (
    <div className="mb-6 flex items-center justify-between">
      <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
      <div className="flex items-center gap-3">
        {status ? (
          <Badge
            label={isRunning ? "Running" : "Stopped"}
            color={isRunning ? "green" : "gray"}
          />
        ) : (
          <Badge label="Unknown" color="gray" />
        )}
        <Link to={`/projects/${project.id}/history`}>
          <Button variant="secondary">History</Button>
        </Link>
        <Button variant="secondary" disabled>
          Settings
        </Button>
      </div>
    </div>
  );
}
