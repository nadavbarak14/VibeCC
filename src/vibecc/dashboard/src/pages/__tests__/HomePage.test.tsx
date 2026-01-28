import { screen, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HomePage } from "../HomePage";
import { renderWithProviders } from "../../test/test-utils";

describe("HomePage", () => {
  it("shows loading state initially", () => {
    renderWithProviders(<HomePage />);
    expect(screen.getByText("Loading projects...")).toBeInTheDocument();
  });

  it("loads and displays projects", async () => {
    renderWithProviders(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });
    expect(screen.getByText("Backend API")).toBeInTheDocument();
  });
});
