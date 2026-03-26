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

describe("thread-data route", () => {
  it("uses the root ALB backend proxy base for deployed thread-data fetches", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "0";
    process.env.BACKEND_PROXY_BASE_URL = "http://internal-alb/";
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ threads: [{ thread_id: "thread-1" }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    const { GET } = await import("./route");

    const response = await GET(
      new NextRequest("http://127.0.0.1:3000/api/thread-data/rooms/room-dev-default/threads?full=1"),
      {
        params: Promise.resolve({
          segments: ["rooms", "room-dev-default", "threads"],
        }),
      },
    );

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [upstreamUrl, upstreamInit] = fetchSpy.mock.calls[0] ?? [];
    expect(String(upstreamUrl)).toBe("http://internal-alb/api/rooms/room-dev-default/threads?full=1");
    expect(upstreamInit).toEqual({
      method: "GET",
      headers: { "content-type": "application/json" },
      body: null,
    });
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ threads: [{ thread_id: "thread-1" }] });
  });

  it("returns a 404 JSON response when mock mode has no backend", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "1";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));
    const { GET } = await import("./route");

    const response = await GET(
      new NextRequest(
        "http://127.0.0.1:3000/api/thread-data/rooms/room-dev-default/threads/thread-1/known-facts",
      ),
      {
        params: Promise.resolve({
          segments: ["rooms", "room-dev-default", "threads", "thread-1", "known-facts"],
        }),
      },
    );

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({
      error: "Mock backend data unavailable.",
    });
  });
});
