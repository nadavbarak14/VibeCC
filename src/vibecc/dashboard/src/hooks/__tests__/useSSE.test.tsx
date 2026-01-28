import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { useSSE } from "../useSSE";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

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

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useSSE", () => {
  it("creates EventSource with correct URL including project_id", () => {
    renderHook(
      () => useSSE({ projectId: "proj-1" }),
      { wrapper },
    );
    const instances = getInstances();
    expect(instances).toHaveLength(1);
    expect(instances[0].url).toBe("/api/v1/events/stream?project_id=proj-1");
  });

  it("filters by project_id in query string", () => {
    renderHook(
      () => useSSE({ projectId: "proj-42" }),
      { wrapper },
    );
    const instances = getInstances();
    expect(instances[0].url).toContain("project_id=proj-42");
  });

  it("calls onEvent with pipeline_created data", async () => {
    const onEvent = vi.fn();
    renderHook(
      () => useSSE({ projectId: "proj-1", onEvent }),
      { wrapper },
    );
    const es = getInstances()[0];
    act(() => {
      es.simulateEvent("pipeline_created", {
        pipeline_id: "pipe-new",
        project_id: "proj-1",
        ticket_id: "200",
        state: "queued",
      });
    });
    expect(onEvent).toHaveBeenCalledWith({
      type: "pipeline_created",
      data: {
        pipeline_id: "pipe-new",
        project_id: "proj-1",
        ticket_id: "200",
        state: "queued",
      },
    });
  });

  it("calls onEvent with pipeline_updated data", () => {
    const onEvent = vi.fn();
    renderHook(
      () => useSSE({ projectId: "proj-1", onEvent }),
      { wrapper },
    );
    const es = getInstances()[0];
    act(() => {
      es.simulateEvent("pipeline_updated", {
        pipeline_id: "pipe-1",
        state: "coding",
        previous_state: "queued",
      });
    });
    expect(onEvent).toHaveBeenCalledWith({
      type: "pipeline_updated",
      data: {
        pipeline_id: "pipe-1",
        state: "coding",
        previous_state: "queued",
      },
    });
  });

  it("calls onEvent with pipeline_completed data", () => {
    const onEvent = vi.fn();
    renderHook(
      () => useSSE({ projectId: "proj-1", onEvent }),
      { wrapper },
    );
    const es = getInstances()[0];
    act(() => {
      es.simulateEvent("pipeline_completed", {
        pipeline_id: "pipe-1",
        final_state: "merged",
      });
    });
    expect(onEvent).toHaveBeenCalledWith({
      type: "pipeline_completed",
      data: {
        pipeline_id: "pipe-1",
        final_state: "merged",
      },
    });
  });

  it("calls onEvent with log data", () => {
    const onEvent = vi.fn();
    renderHook(
      () => useSSE({ projectId: "proj-1", onEvent }),
      { wrapper },
    );
    const es = getInstances()[0];
    act(() => {
      es.simulateEvent("log", {
        pipeline_id: "pipe-1",
        level: "info",
        message: "Building...",
        timestamp: "2024-01-10T00:00:00Z",
      });
    });
    expect(onEvent).toHaveBeenCalledWith({
      type: "log",
      data: {
        pipeline_id: "pipe-1",
        level: "info",
        message: "Building...",
        timestamp: "2024-01-10T00:00:00Z",
      },
    });
  });

  it("closes EventSource on unmount", () => {
    const { unmount } = renderHook(
      () => useSSE({ projectId: "proj-1" }),
      { wrapper },
    );
    const es = getInstances()[0];
    expect(es.readyState).toBe(1);
    unmount();
    expect(es.readyState).toBe(2);
  });

  it("reconnects on error", () => {
    vi.useFakeTimers();
    try {
      renderHook(
        () => useSSE({ projectId: "proj-1" }),
        { wrapper },
      );
      expect(getInstances()).toHaveLength(1);
      const es = getInstances()[0];

      // Simulate error - the hook closes EventSource and schedules reconnect
      act(() => {
        es.simulateError();
      });

      // Should be closed after error
      expect(es.readyState).toBe(2);

      // Advance timer for reconnect (1000ms base delay)
      act(() => {
        vi.advanceTimersByTime(1100);
      });

      // A new EventSource should have been created
      expect(getInstances()).toHaveLength(2);
      expect(getInstances()[1].url).toBe(
        "/api/v1/events/stream?project_id=proj-1",
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("does not connect when disabled", () => {
    renderHook(
      () => useSSE({ projectId: "proj-1", enabled: false }),
      { wrapper },
    );
    expect(getInstances()).toHaveLength(0);
  });
});
