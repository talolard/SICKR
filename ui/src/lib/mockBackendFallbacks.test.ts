import { describe, expect, it, vi } from "vitest";

describe("mockBackendFallbacks", () => {
  it("detects whether mock backend fallbacks are enabled", async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "1";
    const fallbackModule = await import("./mockBackendFallbacks");
    expect(fallbackModule.mockBackendFallbacksEnabled()).toBe(true);
  });

  it("returns static fallback agents and metadata", async () => {
    vi.resetModules();
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "1";
    const fallbackModule = await import("./mockBackendFallbacks");
    expect(fallbackModule.listMockAgentItems()).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "search", agent_key: "agent_search" }),
        expect.objectContaining({
          name: "floor_plan_intake",
          agent_key: "agent_floor_plan_intake",
        }),
      ]),
    );
    expect(fallbackModule.getMockAgentMetadata("search")).toEqual(
      expect.objectContaining({
        name: "search",
        ag_ui_path: "/ag-ui/agents/search",
      }),
    );
    expect(fallbackModule.getMockAgentMetadata("unknown")).toBeNull();
  });
});
