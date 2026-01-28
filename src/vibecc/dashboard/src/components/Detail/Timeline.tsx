import type { PipelineState } from "../../types/api";

interface TimelineStep {
  label: string;
  state: PipelineState;
}

const steps: TimelineStep[] = [
  { label: "Queued", state: "queued" },
  { label: "Coding", state: "coding" },
  { label: "Testing", state: "testing" },
  { label: "Review", state: "review" },
  { label: "Merged", state: "merged" },
];

const stateOrder: Record<PipelineState, number> = {
  queued: 0,
  coding: 1,
  testing: 2,
  review: 3,
  merged: 4,
  failed: -1,
};

function getStepStatus(
  stepState: PipelineState,
  currentState: PipelineState,
): "completed" | "current" | "pending" {
  if (currentState === "failed") {
    return "pending";
  }
  const stepIdx = stateOrder[stepState];
  const currentIdx = stateOrder[currentState];
  if (stepIdx < currentIdx) return "completed";
  if (stepIdx === currentIdx) return "current";
  return "pending";
}

interface TimelineProps {
  currentState: PipelineState;
}

export function Timeline({ currentState }: TimelineProps) {
  const isFailed = currentState === "failed";

  return (
    <div data-testid="timeline">
      <h4 className="mb-3 text-sm font-semibold text-gray-700">Timeline</h4>
      <div className="space-y-3">
        {steps.map((step, i) => {
          const status = getStepStatus(step.state, currentState);
          return (
            <div key={step.state} className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={`h-3 w-3 rounded-full ${
                    status === "completed"
                      ? "bg-green-500"
                      : status === "current"
                        ? "bg-blue-500 ring-2 ring-blue-200"
                        : "bg-gray-200"
                  }`}
                  data-testid={`timeline-dot-${step.state}`}
                />
                {i < steps.length - 1 && (
                  <div
                    className={`mt-1 h-4 w-0.5 ${
                      status === "completed" ? "bg-green-300" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
              <span
                className={`text-sm ${
                  status === "current"
                    ? "font-semibold text-gray-900"
                    : status === "completed"
                      ? "text-gray-600"
                      : "text-gray-400"
                }`}
                data-testid={`timeline-label-${step.state}`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
        {isFailed && (
          <div className="flex items-center gap-3">
            <div className="flex flex-col items-center">
              <div
                className="h-3 w-3 rounded-full bg-red-500 ring-2 ring-red-200"
                data-testid="timeline-dot-failed"
              />
            </div>
            <span
              className="text-sm font-semibold text-red-600"
              data-testid="timeline-label-failed"
            >
              Failed
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
