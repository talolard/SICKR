import { render, screen } from "@testing-library/react";

import { DefaultToolCallRenderer } from "./DefaultToolCallRenderer";

describe("DefaultToolCallRenderer", () => {
  it("renders run_search_graph result counts from results payload", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="complete"
        result={{
          results: [
            { product_id: "a", product_name: "A" },
            { product_id: "b", product_name: "B" },
          ],
          total_candidates: 2,
          returned_count: 2,
          warning: null,
        }}
        args={{ semantic_query: "corner shelf" }}
        errorMessage={undefined}
      />,
    );

    expect(screen.getByText("Result count: 2")).toBeInTheDocument();
  });

  it("renders tool results for a successful call", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="complete"
        result={{ products: [{ id: "a" }, { id: "b" }] }}
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
    expect(screen.getByText("Result count: 2")).toBeInTheDocument();
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
