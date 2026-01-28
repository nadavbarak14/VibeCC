import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { BoardPage } from "../BoardPage";
import { renderWithProviders } from "../../test/test-utils";

describe("BoardPage", () => {
  it("shows loading state initially", () => {
    renderWithProviders(<BoardPage />, {
      initialEntries: ["/projects/proj-1"],
      routePath: "/projects/:projectId",
    });
    expect(screen.getByText("Loading board...")).toBeInTheDocument();
  });

  it("loads and displays pipelines", async () => {
    renderWithProviders(<BoardPage />, {
      initialEntries: ["/projects/proj-1"],
      routePath: "/projects/:projectId",
    });
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });
    expect(screen.getByText("Add user login")).toBeInTheDocument();
    expect(screen.getByText("Fix navbar styling")).toBeInTheDocument();
  });

  it("opens detail panel when pipeline card is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<BoardPage />, {
      initialEntries: ["/projects/proj-1"],
      routePath: "/projects/:projectId",
    });
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("pipeline-card-pipe-2"));
    expect(screen.getByTestId("pipeline-detail")).toBeInTheDocument();
  });

  it("closes detail panel when overlay is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<BoardPage />, {
      initialEntries: ["/projects/proj-1"],
      routePath: "/projects/:projectId",
    });
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("pipeline-card-pipe-2"));
    expect(screen.getByTestId("pipeline-detail")).toBeInTheDocument();
    await user.click(screen.getByTestId("detail-overlay"));
    expect(screen.queryByTestId("pipeline-detail")).not.toBeInTheDocument();
  });
});
