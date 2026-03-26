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

describe("agents route", () => {
  it("uses the explicit backend proxy base for deployed server-side fetches", async () => {
    process.env.BACKEND_PROXY_BASE_URL = "http://internal-alb/";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ agents: [{ name: "search" }] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/agents?full=1"));

    expect(global.fetch).toHaveBeenCalledWith("http://internal-alb/api/agents?full=1", {
      method: "GET",
      headers: { accept: "application/json" },
    });
    expect(response.status).toBe(200);
  });

  it("returns mock fallback agents when the backend is unavailable in mock mode", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "1";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/agents"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      agents: expect.arrayContaining([
        expect.objectContaining({ name: "search" }),
        expect.objectContaining({ name: "image_analysis" }),
      ]),
    });
  });
});
