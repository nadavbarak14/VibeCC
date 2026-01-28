import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { AutopilotToggle } from "../AutopilotToggle";
import { renderWithProviders } from "../../../test/test-utils";
import type { AutopilotStatus } from "../../../types/api";

const runningStatus: AutopilotStatus = {
  project_id: "proj-1",
  running: true,
  active_pipelines: 2,
  queued_tickets: 5,
};

const stoppedStatus: AutopilotStatus = {
  project_id: "proj-1",
  running: false,
  active_pipelines: 0,
  queued_tickets: 0,
};

describe("AutopilotToggle", () => {
  it("shows Start button when stopped", () => {
    renderWithProviders(
      <AutopilotToggle
        status={stoppedStatus}
        onStart={vi.fn()}
        onStop={vi.fn()}
        isLoading={false}
      />,
    );
    expect(screen.getByTestId("autopilot-toggle")).toHaveTextContent("Start");
  });

  it("shows Stop button when running", () => {
    renderWithProviders(
      <AutopilotToggle
        status={runningStatus}
        onStart={vi.fn()}
        onStop={vi.fn()}
        isLoading={false}
      />,
    );
    expect(screen.getByTestId("autopilot-toggle")).toHaveTextContent("Stop");
  });

  it("calls onStart when Start is clicked", async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    renderWithProviders(
      <AutopilotToggle
        status={stoppedStatus}
        onStart={onStart}
        onStop={vi.fn()}
        isLoading={false}
      />,
    );
    await user.click(screen.getByTestId("autopilot-toggle"));
    expect(onStart).toHaveBeenCalledOnce();
  });

  it("calls onStop after confirmation click", async () => {
    const user = userEvent.setup();
    const onStop = vi.fn();
    renderWithProviders(
      <AutopilotToggle
        status={runningStatus}
        onStart={vi.fn()}
        onStop={onStop}
        isLoading={false}
      />,
    );
    const btn = screen.getByTestId("autopilot-toggle");
    // First click shows confirmation
    await user.click(btn);
    expect(btn).toHaveTextContent("Confirm Stop?");
    expect(onStop).not.toHaveBeenCalled();
    // Second click confirms
    await user.click(btn);
    expect(onStop).toHaveBeenCalledOnce();
  });

  it("disables button while loading", () => {
    renderWithProviders(
      <AutopilotToggle
        status={stoppedStatus}
        onStart={vi.fn()}
        onStop={vi.fn()}
        isLoading={true}
      />,
    );
    const btn = screen.getByTestId("autopilot-toggle");
    expect(btn).toBeDisabled();
    expect(btn).toHaveTextContent("Starting...");
  });

  it("shows Stopping text when loading and running", () => {
    renderWithProviders(
      <AutopilotToggle
        status={runningStatus}
        onStart={vi.fn()}
        onStop={vi.fn()}
        isLoading={true}
      />,
    );
    expect(screen.getByTestId("autopilot-toggle")).toHaveTextContent(
      "Stopping...",
    );
  });
});
