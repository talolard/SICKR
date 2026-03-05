import { render, screen } from "@testing-library/react";

import { DefaultToolCallRenderer } from "./DefaultToolCallRenderer";

describe("DefaultToolCallRenderer", () => {
  it("renders tool results for a successful call", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="complete"
        result={{ count: 2 }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "run_search_graph" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Status: complete")).toBeInTheDocument();
    expect(screen.getByText(/"count": 2/)).toBeInTheDocument();
  });

  it("renders guidance for a failed call", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="failed"
        errorMessage="Timed out after 20s"
      />,
    );

    expect(screen.getByText("Status: failed")).toBeInTheDocument();
    expect(screen.getByText("Action: Retry with updated input.")).toBeInTheDocument();
    expect(screen.getByText("Timed out after 20s")).toBeInTheDocument();
  });
});
