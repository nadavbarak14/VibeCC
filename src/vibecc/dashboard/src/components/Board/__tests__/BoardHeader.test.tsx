import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { BoardHeader } from "../BoardHeader";
import { renderWithProviders } from "../../../test/test-utils";
import {
  mockProjects,
  mockAutopilotStatuses,
} from "../../../test/mocks/handlers";

const defaultProps = {
  project: mockProjects[0],
  status: mockAutopilotStatuses["proj-1"],
  onStart: vi.fn(),
  onStop: vi.fn(),
  isAutopilotLoading: false,
  onSettingsClick: vi.fn(),
  onSyncQueue: vi.fn(),
  isSyncLoading: false,
};

describe("BoardHeader", () => {
  it("shows project name", () => {
    renderWithProviders(<BoardHeader {...defaultProps} />);
    expect(screen.getByText("Frontend App")).toBeInTheDocument();
  });

  it("shows autopilot status badge", () => {
    renderWithProviders(<BoardHeader {...defaultProps} />);
    expect(screen.getByText("Running")).toBeInTheDocument();
  });

  it("shows sync queue button with count", () => {
    renderWithProviders(<BoardHeader {...defaultProps} />);
    expect(screen.getByTestId("sync-queue-btn")).toHaveTextContent(
      "Sync Queue (5)",
    );
  });

  it("disables sync button when queue is empty", () => {
    renderWithProviders(
      <BoardHeader
        {...defaultProps}
        status={{ ...mockAutopilotStatuses["proj-1"], queued_tickets: 0 }}
      />,
    );
    expect(screen.getByTestId("sync-queue-btn")).toBeDisabled();
  });

  it("shows syncing state when loading", () => {
    renderWithProviders(
      <BoardHeader {...defaultProps} isSyncLoading={true} />,
    );
    expect(screen.getByTestId("sync-queue-btn")).toHaveTextContent(
      "Syncing...",
    );
  });

  it("calls onSyncQueue when clicked", async () => {
    const onSyncQueue = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <BoardHeader {...defaultProps} onSyncQueue={onSyncQueue} />,
    );
    await user.click(screen.getByTestId("sync-queue-btn"));
    expect(onSyncQueue).toHaveBeenCalledOnce();
  });
});
