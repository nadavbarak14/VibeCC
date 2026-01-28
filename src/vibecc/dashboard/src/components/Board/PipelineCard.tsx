import type { Pipeline } from "../../types/api";
import { Card } from "../common/Card";

interface PipelineCardProps {
  pipeline: Pipeline;
  onClick?: () => void;
}

function StateIndicator({ pipeline }: { pipeline: Pipeline }) {
  switch (pipeline.state) {
    case "coding":
      return (
        <span className="text-xs text-pipeline-coding">Generating code...</span>
      );
    case "testing":
      return (
        <span className="text-xs text-pipeline-testing">
          CI {pipeline.retry_count_ci > 0 ? `(attempt ${pipeline.retry_count_ci + 1})` : "running"}
        </span>
      );
    case "review":
      return (
        <span className="text-xs text-pipeline-review">
          PR review {pipeline.retry_count_review > 0 ? `(attempt ${pipeline.retry_count_review + 1})` : "pending"}
        </span>
      );
    case "failed":
      return (
        <span className="text-xs text-pipeline-failed" data-testid="retry-count">
          {pipeline.retry_count_ci + pipeline.retry_count_review}/
          {pipeline.retry_count_ci + pipeline.retry_count_review} retries used
        </span>
      );
    default:
      return null;
  }
}

export function PipelineCard({ pipeline, onClick }: PipelineCardProps) {
  return (
    <Card
      clickable
      onClick={onClick}
      data-testid={`pipeline-card-${pipeline.id}`}
      className="pipeline-card mb-2"
    >
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <span className="text-xs font-medium text-gray-500">
            #{pipeline.ticket_id}
          </span>
        </div>
        <p className="mt-1 text-sm font-medium text-gray-900 line-clamp-2">
          {pipeline.ticket_title}
        </p>
        <div className="mt-2">
          <StateIndicator pipeline={pipeline} />
        </div>
      </div>
    </Card>
  );
}
