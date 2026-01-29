import { screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PipelineCard } from "../PipelineCard";
import { renderWithProviders } from "../../../test/test-utils";
import { mockPipelines } from "../../../test/mocks/handlers";
import type { Pipeline } from "../../../types/api";

describe("PipelineCard", () => {
  it("displays ticket number", () => {
    renderWithProviders(<PipelineCard pipeline={mockPipelines[0]} />);
    expect(screen.getByText("#101")).toBeInTheDocument();
  });

  it("displays ticket title", () => {
    renderWithProviders(<PipelineCard pipeline={mockPipelines[0]} />);
    expect(screen.getByText("Add user login")).toBeInTheDocument();
  });

  it("shows progress indicator when coding", () => {
    const codingPipeline = mockPipelines.find((p) => p.state === "coding")!;
    renderWithProviders(<PipelineCard pipeline={codingPipeline} />);
    expect(screen.getByText("Generating code...")).toBeInTheDocument();
  });

  it("shows CI status when testing", () => {
    const testingPipeline = mockPipelines.find((p) => p.state === "testing")!;
    renderWithProviders(<PipelineCard pipeline={testingPipeline} />);
    expect(screen.getByText("CI (attempt 2)")).toBeInTheDocument();
  });

  it("shows retry count when failed", () => {
    const failedPipeline = mockPipelines.find((p) => p.state === "failed")!;
    renderWithProviders(<PipelineCard pipeline={failedPipeline} />);
    expect(screen.getByTestId("retry-count")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineCard pipeline={mockPipelines[0]} onClick={onClick} />,
    );
    await user.click(screen.getByTestId("pipeline-card-pipe-1"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  describe("elapsed time", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("shows elapsed time for queued pipeline", () => {
      const now = new Date("2024-01-10T00:30:00Z");
      vi.setSystemTime(now);

      const queuedPipeline = mockPipelines.find((p) => p.state === "queued")!;
      renderWithProviders(<PipelineCard pipeline={queuedPipeline} />);

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("30m");
    });

    it("shows elapsed time for coding pipeline", () => {
      const now = new Date("2024-01-10T02:30:00Z");
      vi.setSystemTime(now);

      const codingPipeline = mockPipelines.find((p) => p.state === "coding")!;
      renderWithProviders(<PipelineCard pipeline={codingPipeline} />);

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("1h 30m");
    });

    it("shows elapsed time for testing pipeline", () => {
      const now = new Date("2024-01-10T02:45:00Z");
      vi.setSystemTime(now);

      const testingPipeline = mockPipelines.find((p) => p.state === "testing")!;
      renderWithProviders(<PipelineCard pipeline={testingPipeline} />);

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("45m");
    });

    it("does not show elapsed time for merged pipeline", () => {
      const now = new Date("2024-01-10T00:00:00Z");
      vi.setSystemTime(now);

      const mergedPipeline = mockPipelines.find((p) => p.state === "merged")!;
      renderWithProviders(<PipelineCard pipeline={mergedPipeline} />);

      expect(screen.queryByTestId("elapsed-time")).not.toBeInTheDocument();
    });

    it("does not show elapsed time for failed pipeline", () => {
      const now = new Date("2024-01-10T00:00:00Z");
      vi.setSystemTime(now);

      const failedPipeline = mockPipelines.find((p) => p.state === "failed")!;
      renderWithProviders(<PipelineCard pipeline={failedPipeline} />);

      expect(screen.queryByTestId("elapsed-time")).not.toBeInTheDocument();
    });

    it("formats time as Xm when under 60 minutes", () => {
      const now = new Date("2024-01-10T00:45:00Z");
      vi.setSystemTime(now);

      const pipeline: Pipeline = {
        ...mockPipelines[0],
        created_at: "2024-01-10T00:00:00Z",
        state: "coding",
      };
      renderWithProviders(<PipelineCard pipeline={pipeline} />);

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("45m");
    });

    it("formats time as Xh Ym when over 60 minutes", () => {
      const now = new Date("2024-01-10T03:15:00Z");
      vi.setSystemTime(now);

      const pipeline: Pipeline = {
        ...mockPipelines[0],
        created_at: "2024-01-10T00:00:00Z",
        state: "coding",
      };
      renderWithProviders(<PipelineCard pipeline={pipeline} />);

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("3h 15m");
    });

    it("updates elapsed time every 60 seconds", () => {
      const initialTime = new Date("2024-01-10T00:30:00Z");
      vi.setSystemTime(initialTime);

      const pipeline: Pipeline = {
        ...mockPipelines[0],
        created_at: "2024-01-10T00:00:00Z",
        state: "coding",
      };
      renderWithProviders(<PipelineCard pipeline={pipeline} />);

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("30m");

      // Advance time by 60 seconds
      act(() => {
        vi.advanceTimersByTime(60000);
      });

      expect(screen.getByTestId("elapsed-time")).toHaveTextContent("31m");
    });
  });
});
