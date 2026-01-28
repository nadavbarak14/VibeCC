import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ProjectCard } from "../ProjectCard";
import { renderWithProviders } from "../../../test/test-utils";
import { mockProjects } from "../../../test/mocks/handlers";

const mockedNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockedNavigate };
});

describe("ProjectCard", () => {
  beforeEach(() => {
    mockedNavigate.mockReset();
  });

  it("renders the project name", () => {
    renderWithProviders(<ProjectCard project={mockProjects[0]} />);
    expect(screen.getByText("Frontend App")).toBeInTheDocument();
  });

  it("renders the repo identifier", () => {
    renderWithProviders(<ProjectCard project={mockProjects[0]} />);
    expect(screen.getByText("acme/frontend")).toBeInTheDocument();
  });

  it("shows Running badge when autopilot is running", async () => {
    renderWithProviders(<ProjectCard project={mockProjects[0]} />);
    await waitFor(() => {
      expect(screen.getByText("Running")).toBeInTheDocument();
    });
  });

  it("shows Stopped badge when autopilot is not running", async () => {
    renderWithProviders(<ProjectCard project={mockProjects[1]} />);
    await waitFor(() => {
      expect(screen.getByText("Stopped")).toBeInTheDocument();
    });
  });

  it("shows active pipeline count", async () => {
    renderWithProviders(<ProjectCard project={mockProjects[0]} />);
    await waitFor(() => {
      expect(screen.getByTestId("pipeline-count")).toHaveTextContent(
        "2 active pipelines",
      );
    });
  });

  it("navigates to project detail on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ProjectCard project={mockProjects[0]} />);
    await user.click(screen.getByTestId("project-card-proj-1"));
    expect(mockedNavigate).toHaveBeenCalledWith("/projects/proj-1");
  });
});
