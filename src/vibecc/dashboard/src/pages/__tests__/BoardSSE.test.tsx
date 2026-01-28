import { screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { BoardPage } from "../BoardPage";
import { renderWithProviders } from "../../test/test-utils";
import { mockPipelines } from "../../test/mocks/handlers";
import type { Pipeline, APIResponse } from "../../types/api";

// Access MockEventSource instances from global setup
function getInstances() {
  return (EventSource as unknown as { instances: Array<{
    url: string;
    readyState: number;
    close: () => void;
    simulateEvent: (type: string, data: unknown) => void;
    simulateError: () => void;
  }> }).instances;
}

function renderBoard() {
  return renderWithProviders(<BoardPage />, {
    initialEntries: ["/projects/proj-1"],
    routePath: "/projects/:projectId",
  });
}

describe("Board SSE Integration", () => {
  it("shows Live indicator when SSE is connected", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });
    // MockEventSource fires onopen via queueMicrotask
    await waitFor(() => {
      expect(screen.getByTestId("sse-status")).toHaveTextContent("Live");
    });
  });

  it("updates board when pipeline_created event received", async () => {
    const { server } = await import("../../test/mocks/server");

    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    // Wait for SSE to connect
    await waitFor(() => {
      expect(getInstances().length).toBeGreaterThan(0);
    });

    // Set up a modified response with a new pipeline
    const newPipeline: Pipeline = {
      id: "pipe-new",
      project_id: "proj-1",
      ticket_id: "200",
      ticket_title: "New pipeline task",
      ticket_body: "Brand new",
      state: "queued",
      branch_name: "ticket-200",
      pr_id: null,
      pr_url: null,
      retry_count_ci: 0,
      retry_count_review: 0,
      feedback: null,
      created_at: "2024-01-11T00:00:00Z",
      updated_at: "2024-01-11T00:00:00Z",
    };

    server.use(
      http.get("/api/v1/pipelines", () => {
        return HttpResponse.json({
          data: [...mockPipelines.filter((p) => p.project_id === "proj-1"), newPipeline],
          error: null,
        } satisfies APIResponse<Pipeline[]>);
      }),
    );

    // Simulate pipeline_created SSE event - triggers cache invalidation
    const es = getInstances().find((i) =>
      i.url.includes("project_id=proj-1"),
    )!;
    act(() => {
      es.simulateEvent("pipeline_created", {
        pipeline_id: "pipe-new",
        project_id: "proj-1",
        ticket_id: "200",
        state: "queued",
      });
    });

    // The new pipeline should appear after refetch
    await waitFor(() => {
      expect(screen.getByText("New pipeline task")).toBeInTheDocument();
    });
  });

  it("updates board when pipeline_updated event received", async () => {
    const { server } = await import("../../test/mocks/server");

    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(getInstances().length).toBeGreaterThan(0);
    });

    // Modify pipe-1 state from queued to coding
    const updatedPipelines = mockPipelines
      .filter((p) => p.project_id === "proj-1")
      .map((p) =>
        p.id === "pipe-1" ? { ...p, state: "coding" as const } : p,
      );

    server.use(
      http.get("/api/v1/pipelines", () => {
        return HttpResponse.json({
          data: updatedPipelines,
          error: null,
        } satisfies APIResponse<Pipeline[]>);
      }),
    );

    const es = getInstances().find((i) =>
      i.url.includes("project_id=proj-1"),
    )!;
    act(() => {
      es.simulateEvent("pipeline_updated", {
        pipeline_id: "pipe-1",
        state: "coding",
        previous_state: "queued",
      });
    });

    // Queue column count should decrease (was 2, now 1)
    await waitFor(() => {
      expect(screen.getByTestId("count-queued")).toHaveTextContent("(1)");
    });
    // Coding column count should increase (was 1, now 2)
    expect(screen.getByTestId("count-coding")).toHaveTextContent("(2)");
  });

  it("updates board when pipeline_completed event received", async () => {
    const { server } = await import("../../test/mocks/server");

    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(getInstances().length).toBeGreaterThan(0);
    });

    // Move pipe-2 from coding to merged
    const updatedPipelines = mockPipelines
      .filter((p) => p.project_id === "proj-1")
      .map((p) =>
        p.id === "pipe-2" ? { ...p, state: "merged" as const } : p,
      );

    server.use(
      http.get("/api/v1/pipelines", () => {
        return HttpResponse.json({
          data: updatedPipelines,
          error: null,
        } satisfies APIResponse<Pipeline[]>);
      }),
    );

    const es = getInstances().find((i) =>
      i.url.includes("project_id=proj-1"),
    )!;
    act(() => {
      es.simulateEvent("pipeline_completed", {
        pipeline_id: "pipe-2",
        final_state: "merged",
      });
    });

    // Merged column should now have 2 (was 1)
    await waitFor(() => {
      expect(screen.getByTestId("count-merged")).toHaveTextContent("(2)");
    });
    // Coding column should now have 0 (was 1)
    expect(screen.getByTestId("count-coding")).toHaveTextContent("(0)");
  });

  it("streams log events to detail panel", async () => {
    const user = userEvent.setup();
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    // Open a pipeline detail panel (pipe-2 is "coding" state, SSE active)
    await user.click(screen.getByTestId("pipeline-card-pipe-2"));
    expect(screen.getByTestId("pipeline-detail")).toBeInTheDocument();

    // Wait for PipelineDetail's SSE connection
    await waitFor(() => {
      const logInstances = getInstances().filter((i) =>
        i.url.includes("project_id=proj-1"),
      );
      expect(logInstances.length).toBeGreaterThanOrEqual(2);
    });

    // Find the PipelineDetail's EventSource (latest one)
    const logEs = getInstances()[getInstances().length - 1];

    // Simulate a log event for pipe-2
    act(() => {
      logEs.simulateEvent("log", {
        pipeline_id: "pipe-2",
        level: "info",
        message: "Compiling source code...",
        timestamp: "2024-01-10T05:00:00Z",
      });
    });

    await waitFor(() => {
      expect(
        screen.getByText("Compiling source code..."),
      ).toBeInTheDocument();
    });
  });

  it("applies animation class to pipeline cards", async () => {
    renderBoard();
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });
    const card = screen.getByTestId("pipeline-card-pipe-1");
    expect(card).toHaveClass("pipeline-card");
  });
});
