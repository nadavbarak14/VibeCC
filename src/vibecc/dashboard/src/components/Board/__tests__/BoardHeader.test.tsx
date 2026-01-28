import { screen } from "@testing-library/react";
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
});
