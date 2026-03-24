import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("health route", () => {
  it("proxies readiness to the backend health route", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/health?full=1"));

    expect(fetchSpy).toHaveBeenCalledWith(expect.stringMatching(/:8000\/api\/health\?full=1$/), {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    await expect(response.json()).resolves.toEqual({ status: "ok" });
  });

  it("preserves non-200 upstream responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "not_ready" }), {
          status: 503,
          headers: { "content-type": "application/problem+json" },
        }),
      ),
    );
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/health"));

    expect(response.status).toBe(503);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    await expect(response.json()).resolves.toEqual({ status: "not_ready" });
  });
});
