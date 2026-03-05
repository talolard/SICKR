import { render, screen } from "@testing-library/react";

import { DefaultToolCallRenderer } from "./DefaultToolCallRenderer";

describe("DefaultToolCallRenderer", () => {
  it("renders tool results for a successful call", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="complete"
        result={{ count: 2 }}
        args={{ semantic_query: "low light hallway plants" }}
        errorMessage={undefined}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "run_search_graph" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Status: complete")).toBeInTheDocument();
    expect(
      screen.getByText("Search query: low light hallway plants"),
    ).toBeInTheDocument();
    expect(screen.getByText(/"count": 2/)).toBeInTheDocument();
  });

  it("renders guidance for a failed call", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="failed"
        result={undefined}
        args={undefined}
        errorMessage="Timed out after 20s"
      />,
    );

    expect(screen.getByText("Status: failed")).toBeInTheDocument();
    expect(screen.getByText("Action: Retry with updated input.")).toBeInTheDocument();
    expect(screen.getByText("Timed out after 20s")).toBeInTheDocument();
  });
});
