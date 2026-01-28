import { Link } from "react-router-dom";
import type { Project, AutopilotStatus, SSEStatus } from "../../types/api";
import { Badge } from "../common/Badge";
import { Button } from "../common/Button";

interface BoardHeaderProps {
  project: Project;
  status?: AutopilotStatus;
  sseStatus?: SSEStatus;
}

const sseLabels: Record<SSEStatus, string> = {
  connected: "Live",
  connecting: "Reconnecting",
  disconnected: "Disconnected",
};

const sseColors: Record<SSEStatus, "green" | "yellow" | "gray"> = {
  connected: "green",
  connecting: "yellow",
  disconnected: "gray",
};

export function BoardHeader({ project, status, sseStatus }: BoardHeaderProps) {
  const isRunning = status?.running ?? false;

  return (
    <div className="mb-6 flex items-center justify-between">
      <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
      <div className="flex items-center gap-3">
        {sseStatus && (
          <span data-testid="sse-status">
            <Badge
              label={sseLabels[sseStatus]}
              color={sseColors[sseStatus]}
            />
          </span>
        )}
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
