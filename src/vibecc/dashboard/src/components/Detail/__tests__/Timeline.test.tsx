import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Timeline } from "../Timeline";
import { renderWithProviders } from "../../../test/test-utils";

describe("Timeline", () => {
  it("renders all timeline events", () => {
    renderWithProviders(<Timeline currentState="coding" />);
    expect(screen.getByTestId("timeline-label-queued")).toBeInTheDocument();
    expect(screen.getByTestId("timeline-label-coding")).toBeInTheDocument();
    expect(screen.getByTestId("timeline-label-testing")).toBeInTheDocument();
    expect(screen.getByTestId("timeline-label-review")).toBeInTheDocument();
    expect(screen.getByTestId("timeline-label-merged")).toBeInTheDocument();
  });

  it("highlights current state differently from completed and pending", () => {
    renderWithProviders(<Timeline currentState="testing" />);
    // Queued and Coding are completed (green dot)
    const queuedDot = screen.getByTestId("timeline-dot-queued");
    expect(queuedDot.className).toContain("bg-green-500");

    const codingDot = screen.getByTestId("timeline-dot-coding");
    expect(codingDot.className).toContain("bg-green-500");

    // Testing is current (blue dot with ring)
    const testingDot = screen.getByTestId("timeline-dot-testing");
    expect(testingDot.className).toContain("bg-blue-500");

    // Review and Merged are pending (gray dot)
    const reviewDot = screen.getByTestId("timeline-dot-review");
    expect(reviewDot.className).toContain("bg-gray-200");
  });

  it("shows failed state when pipeline has failed", () => {
    renderWithProviders(<Timeline currentState="failed" />);
    expect(screen.getByTestId("timeline-dot-failed")).toBeInTheDocument();
    expect(screen.getByTestId("timeline-label-failed")).toHaveTextContent(
      "Failed",
    );
  });
});
