import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatsBar } from "../StatsBar";
import { renderWithProviders } from "../../../test/test-utils";
import { mockHistoryStats } from "../../../test/mocks/handlers";

describe("StatsBar", () => {
  it("shows total completed count", () => {
    renderWithProviders(<StatsBar stats={mockHistoryStats} />);
    expect(screen.getByTestId("stat-total")).toHaveTextContent("3");
  });

  it("shows success rate percentage", () => {
    renderWithProviders(<StatsBar stats={mockHistoryStats} />);
    // 2 merged / 3 total = 67%
    expect(screen.getByTestId("stat-success-rate")).toHaveTextContent("67%");
  });

  it("shows formatted average duration", () => {
    renderWithProviders(<StatsBar stats={mockHistoryStats} />);
    // 7800 seconds = 2h 10m
    expect(screen.getByTestId("stat-avg-duration")).toHaveTextContent("2h 10m");
  });

  it("shows average retries", () => {
    renderWithProviders(<StatsBar stats={mockHistoryStats} />);
    expect(screen.getByTestId("stat-avg-retries")).toHaveTextContent(
      "1.3 CI / 0.3 Review",
    );
  });

  it("shows 0% success rate when no completions", () => {
    const emptyStats = {
      ...mockHistoryStats,
      total_completed: 0,
      total_merged: 0,
      total_failed: 0,
    };
    renderWithProviders(<StatsBar stats={emptyStats} />);
    expect(screen.getByTestId("stat-success-rate")).toHaveTextContent("0%");
  });
});
