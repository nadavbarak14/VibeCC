import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProjectGrid } from "../ProjectGrid";
import { renderWithProviders } from "../../../test/test-utils";
import { mockProjects } from "../../../test/mocks/handlers";

describe("ProjectGrid", () => {
  it("renders all project cards", () => {
    renderWithProviders(<ProjectGrid projects={mockProjects} />);
    expect(screen.getByText("Frontend App")).toBeInTheDocument();
    expect(screen.getByText("Backend API")).toBeInTheDocument();
  });

  it("shows empty state when no projects", () => {
    renderWithProviders(<ProjectGrid projects={[]} />);
    expect(screen.getByText("No projects yet")).toBeInTheDocument();
  });
});
