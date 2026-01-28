import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { HistoryTable } from "../HistoryTable";
import { renderWithProviders } from "../../../test/test-utils";
import { mockHistory } from "../../../test/mocks/handlers";

describe("HistoryTable", () => {
  it("renders all history rows", () => {
    renderWithProviders(
      <HistoryTable
        items={mockHistory}
        page={0}
        onPageChange={vi.fn()}
        hasMore={false}
      />,
    );
    expect(screen.getByTestId("history-row-hist-1")).toBeInTheDocument();
    expect(screen.getByTestId("history-row-hist-2")).toBeInTheDocument();
    expect(screen.getByTestId("history-row-hist-3")).toBeInTheDocument();
  });

  it("shows merged badge in green", () => {
    renderWithProviders(
      <HistoryTable
        items={[mockHistory[0]]}
        page={0}
        onPageChange={vi.fn()}
        hasMore={false}
      />,
    );
    const badge = screen.getByText("merged");
    expect(badge).toHaveClass("bg-green-100");
  });

  it("shows failed badge in red", () => {
    renderWithProviders(
      <HistoryTable
        items={[mockHistory[2]]}
        page={0}
        onPageChange={vi.fn()}
        hasMore={false}
      />,
    );
    const badge = screen.getByText("failed");
    expect(badge).toHaveClass("bg-red-100");
  });

  it("formats duration as human-readable", () => {
    renderWithProviders(
      <HistoryTable
        items={[mockHistory[0]]}
        page={0}
        onPageChange={vi.fn()}
        hasMore={false}
      />,
    );
    // 5400 seconds = 1h 30m
    expect(screen.getByTestId("duration-hist-1")).toHaveTextContent("1h 30m");
  });

  it("shows empty state when no items", () => {
    renderWithProviders(
      <HistoryTable
        items={[]}
        page={0}
        onPageChange={vi.fn()}
        hasMore={false}
      />,
    );
    expect(screen.getByTestId("history-empty")).toBeInTheDocument();
    expect(screen.getByText("No history to show.")).toBeInTheDocument();
  });

  it("navigates to next page", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    renderWithProviders(
      <HistoryTable
        items={mockHistory}
        page={0}
        onPageChange={onPageChange}
        hasMore={true}
      />,
    );
    await user.click(screen.getByTestId("page-next"));
    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it("disables previous button on first page", () => {
    renderWithProviders(
      <HistoryTable
        items={mockHistory}
        page={0}
        onPageChange={vi.fn()}
        hasMore={true}
      />,
    );
    expect(screen.getByTestId("page-prev")).toBeDisabled();
  });

  it("disables next button when no more pages", () => {
    renderWithProviders(
      <HistoryTable
        items={mockHistory}
        page={0}
        onPageChange={vi.fn()}
        hasMore={false}
      />,
    );
    expect(screen.getByTestId("page-next")).toBeDisabled();
  });
});
