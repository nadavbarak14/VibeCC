import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BoardHeader } from "../BoardHeader";
import { renderWithProviders } from "../../../test/test-utils";
import {
  mockProjects,
  mockAutopilotStatuses,
} from "../../../test/mocks/handlers";

describe("BoardHeader", () => {
  it("shows project name", () => {
    renderWithProviders(
      <BoardHeader
        project={mockProjects[0]}
        status={mockAutopilotStatuses["proj-1"]}
      />,
    );
    expect(screen.getByText("Frontend App")).toBeInTheDocument();
  });

  it("shows autopilot status badge", () => {
    renderWithProviders(
      <BoardHeader
        project={mockProjects[0]}
        status={mockAutopilotStatuses["proj-1"]}
      />,
    );
    expect(screen.getByText("Running")).toBeInTheDocument();
  });
});
