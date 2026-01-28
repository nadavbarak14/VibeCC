import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { KanbanColumn } from "../KanbanColumn";
import { renderWithProviders } from "../../../test/test-utils";
import { mockPipelines } from "../../../test/mocks/handlers";

const queuedPipelines = mockPipelines.filter((p) => p.state === "queued");

describe("KanbanColumn", () => {
  it("renders column title", () => {
    renderWithProviders(
      <KanbanColumn
        title="Queue"
        state="queued"
        pipelines={queuedPipelines}
        colorClass="bg-pipeline-queued"
      />,
    );
    expect(screen.getByText("Queue")).toBeInTheDocument();
  });

  it("renders pipeline count", () => {
    renderWithProviders(
      <KanbanColumn
        title="Queue"
        state="queued"
        pipelines={queuedPipelines}
        colorClass="bg-pipeline-queued"
      />,
    );
    expect(screen.getByTestId("count-queued")).toHaveTextContent(
      `(${queuedPipelines.length})`,
    );
  });

  it("renders all pipeline cards", () => {
    renderWithProviders(
      <KanbanColumn
        title="Queue"
        state="queued"
        pipelines={queuedPipelines}
        colorClass="bg-pipeline-queued"
      />,
    );
    expect(screen.getByText("Add user login")).toBeInTheDocument();
    expect(screen.getByText("Add search feature")).toBeInTheDocument();
  });

  it("shows empty state when no pipelines", () => {
    renderWithProviders(
      <KanbanColumn
        title="Review"
        state="review"
        pipelines={[]}
        colorClass="bg-pipeline-review"
      />,
    );
    expect(screen.getByText("No pipelines")).toBeInTheDocument();
  });
});
