import { useState, useEffect } from "react";
import type { Pipeline, Project } from "../../types/api";
import { useLogStream } from "../../hooks/useLogStream";
import { Timeline } from "./Timeline";
import { LogStream } from "./LogStream";

interface PipelineDetailProps {
  pipeline: Pipeline;
  project: Project;
  onClose: () => void;
}

export function PipelineDetail({
  pipeline,
  project,
  onClose,
}: PipelineDetailProps) {
  const [descExpanded, setDescExpanded] = useState(false);
  const { logs } = useLogStream({
    projectId: pipeline.project_id,
    pipelineId: pipeline.id,
    enabled: pipeline.state !== "merged" && pipeline.state !== "failed",
  });

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={onClose}
        data-testid="detail-overlay"
      />
      <div
        className="fixed inset-y-0 right-0 z-50 w-full max-w-lg overflow-y-auto bg-white shadow-xl transition-transform"
        data-testid="pipeline-detail"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-gray-200 p-4">
          <div>
            <span className="text-sm text-gray-500">#{pipeline.ticket_id}</span>
            <h2 className="text-lg font-semibold text-gray-900">
              {pipeline.ticket_title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            data-testid="detail-close"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-6 p-4">
          {/* Status Bar */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Status</span>
              <span className="font-medium uppercase text-gray-900">
                {pipeline.state}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Branch</span>
              <span className="font-mono text-gray-900">
                {pipeline.branch_name}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">PR</span>
              {pipeline.pr_url ? (
                <a
                  href={pipeline.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                  data-testid="pr-link"
                >
                  #{pipeline.pr_id}
                </a>
              ) : (
                <span className="text-gray-400" data-testid="pr-placeholder">
                  -
                </span>
              )}
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Retries</span>
              <span className="text-gray-900" data-testid="retry-counts">
                CI {pipeline.retry_count_ci}/{project.max_retries_ci} | Review{" "}
                {pipeline.retry_count_review}/{project.max_retries_review}
              </span>
            </div>
          </div>

          {/* Timeline */}
          <Timeline currentState={pipeline.state} />

          {/* Live Logs */}
          <LogStream logs={logs} />

          {/* Ticket Description */}
          <div>
            <button
              onClick={() => setDescExpanded((prev) => !prev)}
              className="flex w-full items-center gap-1 text-sm font-semibold text-gray-700"
              data-testid="desc-toggle"
            >
              <span className="text-xs">{descExpanded ? "▼" : "▶"}</span>
              Ticket Description
            </button>
            {descExpanded && (
              <p
                className="mt-2 whitespace-pre-wrap text-sm text-gray-600"
                data-testid="desc-content"
              >
                {pipeline.ticket_body}
              </p>
            )}
          </div>

          {/* Feedback */}
          {pipeline.feedback && (
            <div data-testid="feedback-section">
              <h4 className="text-sm font-semibold text-red-600">Feedback</h4>
              <p className="mt-1 text-sm text-gray-600">{pipeline.feedback}</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
