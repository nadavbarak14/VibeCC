import { screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { LogStream } from "../LogStream";
import { renderWithProviders } from "../../../test/test-utils";
import type { LogEntry } from "../../../types/api";

const mockLogs: LogEntry[] = [
  {
    pipeline_id: "pipe-1",
    level: "info",
    message: "Reading ticket requirements...",
    timestamp: "2024-01-10T10:30:00Z",
  },
  {
    pipeline_id: "pipe-1",
    level: "info",
    message: "Analyzing codebase...",
    timestamp: "2024-01-10T10:30:05Z",
  },
];

describe("LogStream", () => {
  it("renders log messages", () => {
    renderWithProviders(<LogStream logs={mockLogs} />);
    expect(
      screen.getByText("Reading ticket requirements..."),
    ).toBeInTheDocument();
    expect(screen.getByText("Analyzing codebase...")).toBeInTheDocument();
  });

  it("auto-scrolls on new logs", () => {
    const scrollSpy = vi.spyOn(Element.prototype, "scrollIntoView");
    const { rerender } = renderWithProviders(<LogStream logs={mockLogs} />);
    const newLogs = [
      ...mockLogs,
      {
        pipeline_id: "pipe-1",
        level: "info",
        message: "Writing code...",
        timestamp: "2024-01-10T10:30:10Z",
      },
    ];
    rerender(<LogStream logs={newLogs} />);
    expect(scrollSpy).toHaveBeenCalled();
    scrollSpy.mockRestore();
  });

  it("shows empty state when no logs", () => {
    renderWithProviders(<LogStream logs={[]} />);
    expect(screen.getByText("Waiting for logs...")).toBeInTheDocument();
  });
});
