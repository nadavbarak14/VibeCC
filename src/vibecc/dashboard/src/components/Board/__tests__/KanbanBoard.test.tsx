import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { KanbanBoard } from "../KanbanBoard";
import { renderWithProviders } from "../../../test/test-utils";
import { mockPipelines } from "../../../test/mocks/handlers";

describe("KanbanBoard", () => {
  it("groups pipelines by state into correct columns", () => {
    renderWithProviders(<KanbanBoard pipelines={mockPipelines} />);

    expect(screen.getByTestId("count-queued")).toHaveTextContent("(2)");
    expect(screen.getByTestId("count-coding")).toHaveTextContent("(1)");
    expect(screen.getByTestId("count-testing")).toHaveTextContent("(1)");
    expect(screen.getByTestId("count-review")).toHaveTextContent("(0)");
    expect(screen.getByTestId("count-merged")).toHaveTextContent("(1)");
    expect(screen.getByTestId("count-failed")).toHaveTextContent("(1)");
  });
});
