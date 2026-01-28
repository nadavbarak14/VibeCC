import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PipelineDetail } from "../PipelineDetail";
import { renderWithProviders } from "../../../test/test-utils";
import { mockPipelines, mockProjects } from "../../../test/mocks/handlers";

const project = mockProjects[0];
const queuedPipeline = mockPipelines[0]; // queued, no PR, no feedback
const testingPipeline = mockPipelines[2]; // testing, has PR
const failedPipeline = mockPipelines[4]; // failed, has feedback

describe("PipelineDetail", () => {
  it("shows ticket number and title", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("#101")).toBeInTheDocument();
    expect(screen.getByText("Add user login")).toBeInTheDocument();
  });

  it("shows current state", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("queued")).toBeInTheDocument();
  });

  it("shows branch name", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText("ticket-101")).toBeInTheDocument();
  });

  it("shows PR link when available", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={testingPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    const link = screen.getByTestId("pr-link");
    expect(link).toHaveAttribute(
      "href",
      "https://github.com/acme/frontend/pull/10",
    );
    expect(link).toHaveTextContent("#10");
  });

  it("shows placeholder when no PR", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByTestId("pr-placeholder")).toHaveTextContent("-");
  });

  it("shows retry counts", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={failedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByTestId("retry-counts")).toHaveTextContent(
      "CI 3/3 | Review 0/3",
    );
  });

  it("shows feedback when present", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={failedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByTestId("feedback-section")).toBeInTheDocument();
    expect(
      screen.getByText("CI failed after max retries"),
    ).toBeInTheDocument();
  });

  it("hides feedback when empty", () => {
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("feedback-section")).not.toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={onClose}
      />,
    );
    await user.click(screen.getByTestId("detail-close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when overlay clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(
      <PipelineDetail
        pipeline={queuedPipeline}
        project={project}
        onClose={onClose}
      />,
    );
    await user.click(screen.getByTestId("detail-overlay"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
