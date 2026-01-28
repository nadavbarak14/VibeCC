import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { HistoryPage } from "../HistoryPage";
import { renderWithProviders } from "../../test/test-utils";

describe("HistoryPage", () => {
  const renderPage = () =>
    renderWithProviders(<HistoryPage />, {
      initialEntries: ["/projects/proj-1/history"],
      routePath: "/projects/:projectId/history",
    });

  it("shows loading state initially", () => {
    renderPage();
    expect(screen.getByText("Loading history...")).toBeInTheDocument();
  });

  it("loads and displays history data", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("History")).toBeInTheDocument();
    });
    expect(screen.getByText("#90")).toBeInTheDocument();
    expect(screen.getByText("Setup CI pipeline")).toBeInTheDocument();
    expect(screen.getByText("#91")).toBeInTheDocument();
    expect(screen.getByText("#92")).toBeInTheDocument();
  });

  it("displays stats bar with correct values", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("stats-bar")).toBeInTheDocument();
    });
    expect(screen.getByTestId("stat-total")).toHaveTextContent("3");
    expect(screen.getByTestId("stat-success-rate")).toHaveTextContent("67%");
  });

  it("filters by status when filter is changed", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("#90")).toBeInTheDocument();
    });
    // Click "Failed" filter
    await user.click(screen.getByTestId("filter-failed"));
    await waitFor(() => {
      expect(screen.getByText("#92")).toBeInTheDocument();
    });
    // Merged items should not be visible
    expect(screen.queryByText("#90")).not.toBeInTheDocument();
  });
});
