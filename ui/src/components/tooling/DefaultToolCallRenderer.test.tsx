import { render, screen } from "@testing-library/react";

import { DefaultToolCallRenderer } from "./DefaultToolCallRenderer";

describe("DefaultToolCallRenderer", () => {
  it("renders run_search_graph result counts from batched results payload", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="complete"
        result={{
          queries: [
            {
              query_id: "a",
              semantic_query: "corner shelf",
              results: [
                { product_id: "a", product_name: "A" },
                { product_id: "b", product_name: "B" },
              ],
            },
          ],
        }}
        args={{
          queries: [{ query_id: "a", semantic_query: "corner shelf" }],
        }}
        errorMessage={undefined}
      />,
    );

    expect(screen.getByText("Result count: 2")).toBeInTheDocument();
  });

  it("renders tool results for a successful batched call", () => {
    render(
      <DefaultToolCallRenderer
        name="run_search_graph"
        status="complete"
        result={{ products: [{ id: "a" }, { id: "b" }] }}
        args={{
          queries: [
            { query_id: "lighting", semantic_query: "low light hallway plants" },
            { query_id: "storage", semantic_query: "narrow shelves" },
          ],
        }}
        errorMessage={undefined}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "run_search_graph" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Status: complete")).toBeInTheDocument();
    expect(
      screen.getByText("Search queries: low light hallway plants · narrow shelves"),
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
