import type { Pipeline, PipelineState } from "../../types/api";
import { PipelineCard } from "./PipelineCard";

interface KanbanColumnProps {
  title: string;
  state: PipelineState;
  pipelines: Pipeline[];
  colorClass: string;
  onCardClick?: (pipeline: Pipeline) => void;
}

export function KanbanColumn({
  title,
  state,
  pipelines,
  colorClass,
  onCardClick,
}: KanbanColumnProps) {
  return (
    <div
      className="flex min-w-[200px] flex-1 flex-col"
      data-testid={`column-${state}`}
    >
      <div className="mb-3 flex items-center gap-2">
        <div className={`h-2.5 w-2.5 rounded-full ${colorClass}`} />
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        <span className="text-xs text-gray-400" data-testid={`count-${state}`}>
          ({pipelines.length})
        </span>
      </div>
      <div className="flex-1 rounded-lg bg-gray-50 p-2">
        {pipelines.length === 0 ? (
          <p className="py-4 text-center text-xs text-gray-400">No pipelines</p>
        ) : (
          pipelines.map((pipeline) => (
            <PipelineCard
              key={pipeline.id}
              pipeline={pipeline}
              onClick={() => onCardClick?.(pipeline)}
            />
          ))
        )}
      </div>
    </div>
  );
}
