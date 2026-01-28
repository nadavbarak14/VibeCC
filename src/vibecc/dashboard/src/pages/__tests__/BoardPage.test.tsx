import { screen, waitFor } from "@testing-library/react";
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
});
