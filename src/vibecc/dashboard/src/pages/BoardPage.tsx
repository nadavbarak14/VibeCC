import { useState } from "react";
import { useParams } from "react-router-dom";
import { useProject } from "../hooks/useProject";
import { usePipelines } from "../hooks/usePipelines";
import { useAutopilotStatus } from "../hooks/useAutopilotStatus";
import { BoardHeader } from "../components/Board/BoardHeader";
import { KanbanBoard } from "../components/Board/KanbanBoard";
import { PipelineDetail } from "../components/Detail/PipelineDetail";
import type { Pipeline } from "../types/api";

export function BoardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading: projectLoading } = useProject(projectId!);
  const { data: pipelines, isLoading: pipelinesLoading } = usePipelines(
    projectId!,
  );
  const { data: status } = useAutopilotStatus(projectId!);
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(
    null,
  );

  if (projectLoading || pipelinesLoading) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-gray-500">Loading board...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="py-12 text-center">
        <h3 className="text-lg font-medium text-red-600">Project not found</h3>
      </div>
    );
  }

  return (
    <div>
      <BoardHeader project={project} status={status} />
      <KanbanBoard
        pipelines={pipelines ?? []}
        onCardClick={setSelectedPipeline}
      />
      {selectedPipeline && (
        <PipelineDetail
          pipeline={selectedPipeline}
          project={project}
          onClose={() => setSelectedPipeline(null)}
        />
      )}
    </div>
  );
}
