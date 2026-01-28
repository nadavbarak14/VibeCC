import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { http, HttpResponse } from "msw";
import { BoardPage } from "../BoardPage";
import { renderWithProviders } from "../../test/test-utils";
import { server } from "../../test/mocks/server";
import type { AutopilotStatus, APIResponse } from "../../types/api";

function renderBoard() {
  return renderWithProviders(<BoardPage />, {
    initialEntries: ["/projects/proj-2"],
    routePath: "/projects/:projectId",
  });
}

function renderRunningBoard() {
  return renderWithProviders(<BoardPage />, {
    initialEntries: ["/projects/proj-1"],
    routePath: "/projects/:projectId",
  });
}

describe("Board Control Integration", () => {
  it("starts autopilot and shows success toast", async () => {
    const user = userEvent.setup();
    renderBoard();

    // Wait for board to load (proj-2 is "Stopped")
    await waitFor(() => {
      expect(screen.getByText("Backend API")).toBeInTheDocument();
    });

    // Should show Start button since proj-2 is stopped
    await waitFor(() => {
      expect(screen.getByTestId("autopilot-toggle")).toHaveTextContent(
        "Start",
      );
    });

    // Override the autopilot status to return running after start
    server.use(
      http.get("/api/v1/projects/proj-2/autopilot", () => {
        return HttpResponse.json({
          data: {
            project_id: "proj-2",
            running: true,
            active_pipelines: 0,
            queued_tickets: 0,
          },
          error: null,
        } satisfies APIResponse<AutopilotStatus>);
      }),
    );

    await user.click(screen.getByTestId("autopilot-toggle"));

    // Toast should appear
    await waitFor(() => {
      expect(screen.getByText("Autopilot started")).toBeInTheDocument();
    });

    // Status should update to Running
    await waitFor(() => {
      expect(screen.getByText("Running")).toBeInTheDocument();
    });
  });

  it("stops autopilot with confirmation and shows success toast", async () => {
    const user = userEvent.setup();
    renderRunningBoard();

    // Wait for board to load (proj-1 is "Running")
    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByTestId("autopilot-toggle")).toHaveTextContent("Stop");
    });

    // Override the autopilot status to return stopped after stop
    server.use(
      http.get("/api/v1/projects/proj-1/autopilot", () => {
        return HttpResponse.json({
          data: {
            project_id: "proj-1",
            running: false,
            active_pipelines: 0,
            queued_tickets: 0,
          },
          error: null,
        } satisfies APIResponse<AutopilotStatus>);
      }),
    );

    // First click - confirmation
    await user.click(screen.getByTestId("autopilot-toggle"));
    expect(screen.getByTestId("autopilot-toggle")).toHaveTextContent(
      "Confirm Stop?",
    );

    // Second click - confirm stop
    await user.click(screen.getByTestId("autopilot-toggle"));

    // Toast should appear
    await waitFor(() => {
      expect(screen.getByText("Autopilot stopped")).toBeInTheDocument();
    });

    // Status should update to Stopped
    await waitFor(() => {
      expect(screen.getByText("Stopped")).toBeInTheDocument();
    });
  });

  it("opens settings modal from board", async () => {
    const user = userEvent.setup();
    renderRunningBoard();

    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Settings"));
    expect(screen.getByTestId("settings-modal")).toBeInTheDocument();
    expect(
      screen.getByText("Settings - Frontend App"),
    ).toBeInTheDocument();
  });

  it("closes settings modal on Close button", async () => {
    const user = userEvent.setup();
    renderRunningBoard();

    await waitFor(() => {
      expect(screen.getByText("Frontend App")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Settings"));
    expect(screen.getByTestId("settings-modal")).toBeInTheDocument();

    await user.click(screen.getByTestId("settings-close-btn"));
    expect(screen.queryByTestId("settings-modal")).not.toBeInTheDocument();
  });
});
