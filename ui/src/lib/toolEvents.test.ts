import { upsertToolCall } from "./toolEvents";

describe("upsertToolCall", () => {
  it("upserts tool updates keyed by tool_call_id", () => {
    const first = upsertToolCall(
      {},
      {
        tool_call_id: "tool-1",
        tool: "run_search_graph",
        status: "executing",
        result: undefined,
        errorMessage: undefined,
      },
    );

    const second = upsertToolCall(first, {
      tool_call_id: "tool-1",
      tool: "run_search_graph",
      status: "complete",
      result: { products: [{ id: "prod-001" }] },
      errorMessage: undefined,
    });

    expect(Object.keys(second)).toHaveLength(1);
    expect(second["tool-1"]?.status).toBe("complete");
    expect(second["tool-1"]?.result).toEqual({ products: [{ id: "prod-001" }] });
  });
});
