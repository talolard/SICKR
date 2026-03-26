import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const originalMockFlag = process.env.NEXT_PUBLIC_USE_MOCK_AGENT;
const originalBackendProxyBaseUrl = process.env.BACKEND_PROXY_BASE_URL;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalMockFlag === undefined) {
    delete process.env.NEXT_PUBLIC_USE_MOCK_AGENT;
  } else {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = originalMockFlag;
  }
  if (originalBackendProxyBaseUrl === undefined) {
    delete process.env.BACKEND_PROXY_BASE_URL;
  } else {
    process.env.BACKEND_PROXY_BASE_URL = originalBackendProxyBaseUrl;
  }
});

describe("agent metadata route", () => {
  it("uses the explicit backend proxy base for deployed metadata fetches", async () => {
    process.env.BACKEND_PROXY_BASE_URL = "http://internal-alb/";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ name: "search", agent_key: "agent_search" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const { GET } = await import("./route");

    const response = await GET(
      new NextRequest("http://127.0.0.1:3000/api/agents/search/metadata?full=1"),
      { params: Promise.resolve({ agent: "search" }) },
    );

    expect(global.fetch).toHaveBeenCalledWith("http://internal-alb/api/agents/search/metadata?full=1", {
      method: "GET",
      headers: { accept: "application/json" },
    });
    expect(response.status).toBe(200);
  });

  it("returns fallback metadata in mock mode when the backend is unavailable", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "1";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));
    const { GET } = await import("./route");

    const response = await GET(
      new NextRequest("http://127.0.0.1:3000/api/agents/search/metadata"),
      { params: Promise.resolve({ agent: "search" }) },
    );

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        name: "search",
        agent_key: "agent_search",
      }),
    );
  });
});
