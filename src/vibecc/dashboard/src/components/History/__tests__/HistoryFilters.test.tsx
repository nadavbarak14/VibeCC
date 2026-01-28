import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { HistoryFilters } from "../HistoryFilters";
import { renderWithProviders } from "../../../test/test-utils";

describe("HistoryFilters", () => {
  it("highlights the active filter", () => {
    renderWithProviders(
      <HistoryFilters value="merged" onChange={vi.fn()} />,
    );
    const mergedButton = screen.getByTestId("filter-merged");
    expect(mergedButton).toHaveClass("bg-gray-900");
  });

  it("calls onChange with merged when clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <HistoryFilters value="all" onChange={onChange} />,
    );
    await user.click(screen.getByTestId("filter-merged"));
    expect(onChange).toHaveBeenCalledWith("merged");
  });

  it("calls onChange with failed when clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <HistoryFilters value="all" onChange={onChange} />,
    );
    await user.click(screen.getByTestId("filter-failed"));
    expect(onChange).toHaveBeenCalledWith("failed");
  });
});
