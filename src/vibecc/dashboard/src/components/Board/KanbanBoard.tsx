import type { Pipeline, PipelineState } from "../../types/api";
import { KanbanColumn } from "./KanbanColumn";

interface ColumnConfig {
  title: string;
  state: PipelineState;
  colorClass: string;
}

const columns: ColumnConfig[] = [
  { title: "Queue", state: "queued", colorClass: "bg-pipeline-queued" },
  { title: "Coding", state: "coding", colorClass: "bg-pipeline-coding" },
  { title: "Testing", state: "testing", colorClass: "bg-pipeline-testing" },
  { title: "Review", state: "review", colorClass: "bg-pipeline-review" },
  { title: "Done", state: "merged", colorClass: "bg-pipeline-merged" },
  { title: "Failed", state: "failed", colorClass: "bg-pipeline-failed" },
];

interface KanbanBoardProps {
  pipelines: Pipeline[];
  onCardClick?: (pipeline: Pipeline) => void;
}

export function KanbanBoard({ pipelines, onCardClick }: KanbanBoardProps) {
  const grouped = new Map<PipelineState, Pipeline[]>();
  for (const col of columns) {
    grouped.set(col.state, []);
  }
  for (const pipeline of pipelines) {
    grouped.get(pipeline.state)?.push(pipeline);
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {columns.map((col) => (
        <KanbanColumn
          key={col.state}
          title={col.title}
          state={col.state}
          pipelines={grouped.get(col.state) ?? []}
          colorClass={col.colorClass}
          onCardClick={onCardClick}
        />
      ))}
    </div>
  );
}
