import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PipelineCard } from "../PipelineCard";
import { renderWithProviders } from "../../../test/test-utils";
import { mockPipelines } from "../../../test/mocks/handlers";

describe("PipelineCard", () => {
  it("displays ticket number", () => {
    renderWithProviders(<PipelineCard pipeline={mockPipelines[0]} />);
    expect(screen.getByText("#101")).toBeInTheDocument();
  });

  it("displays ticket title", () => {
    renderWithProviders(<PipelineCard pipeline={mockPipelines[0]} />);
    expect(screen.getByText("Add user login")).toBeInTheDocument();
  });

  it("shows progress indicator when coding", () => {
    const codingPipeline = mockPipelines.find((p) => p.state === "coding")!;
    renderWithProviders(<PipelineCard pipeline={codingPipeline} />);
    expect(screen.getByText("Generating code...")).toBeInTheDocument();
  });

  it("shows CI status when testing", () => {
    const testingPipeline = mockPipelines.find((p) => p.state === "testing")!;
    renderWithProviders(<PipelineCard pipeline={testingPipeline} />);
    expect(screen.getByText("CI (attempt 2)")).toBeInTheDocument();
  });

  it("shows retry count when failed", () => {
    const failedPipeline = mockPipelines.find((p) => p.state === "failed")!;
    renderWithProviders(<PipelineCard pipeline={failedPipeline} />);
    expect(screen.getByTestId("retry-count")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    renderWithProviders(
      <PipelineCard pipeline={mockPipelines[0]} onClick={onClick} />,
    );
    await user.click(screen.getByTestId("pipeline-card-pipe-1"));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
