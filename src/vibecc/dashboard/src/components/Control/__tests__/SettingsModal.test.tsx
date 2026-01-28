import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { SettingsModal } from "../SettingsModal";
import { renderWithProviders } from "../../../test/test-utils";
import { mockProjects } from "../../../test/mocks/handlers";

describe("SettingsModal", () => {
  it("opens and shows project name in title", () => {
    renderWithProviders(
      <SettingsModal project={mockProjects[0]} onClose={vi.fn()} />,
    );
    expect(screen.getByTestId("settings-modal")).toBeInTheDocument();
    expect(
      screen.getByText("Settings - Frontend App"),
    ).toBeInTheDocument();
  });

  it("shows config values", () => {
    renderWithProviders(
      <SettingsModal project={mockProjects[0]} onClose={vi.fn()} />,
    );
    expect(screen.getByTestId("setting-base-branch")).toHaveTextContent(
      "main",
    );
    expect(screen.getByTestId("setting-max-ci")).toHaveTextContent("3");
    expect(screen.getByTestId("setting-max-review")).toHaveTextContent("3");
  });

  it("closes on X button click", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(
      <SettingsModal project={mockProjects[0]} onClose={onClose} />,
    );
    await user.click(screen.getByTestId("settings-close-x"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes on Close button click", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(
      <SettingsModal project={mockProjects[0]} onClose={onClose} />,
    );
    await user.click(screen.getByTestId("settings-close-btn"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes on overlay click", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(
      <SettingsModal project={mockProjects[0]} onClose={onClose} />,
    );
    await user.click(screen.getByTestId("settings-overlay"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
