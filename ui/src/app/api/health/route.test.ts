import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const originalAppEnv = process.env.APP_ENV;
const originalReleaseVersion = process.env.APP_RELEASE_VERSION;
const originalBackendProxyBaseUrl = process.env.BACKEND_PROXY_BASE_URL;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalAppEnv === undefined) {
    delete process.env.APP_ENV;
  } else {
    process.env.APP_ENV = originalAppEnv;
  }
  if (originalReleaseVersion === undefined) {
    delete process.env.APP_RELEASE_VERSION;
  } else {
    process.env.APP_RELEASE_VERSION = originalReleaseVersion;
  }
  if (originalBackendProxyBaseUrl === undefined) {
    delete process.env.BACKEND_PROXY_BASE_URL;
  } else {
    process.env.BACKEND_PROXY_BASE_URL = originalBackendProxyBaseUrl;
  }
});

describe("ui health routes", () => {
  it("reports live status without calling the backend", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const { GET } = await import("./live/route");

    const response = await GET();

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        status: "ok",
        checks: expect.objectContaining({
          ui: expect.objectContaining({ status: "ok" }),
        }),
      }),
    );
  });

  it("proxies backend readiness through /api/health", async () => {
    process.env.BACKEND_PROXY_BASE_URL = "http://internal-alb:8000/";
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", checks: { database: { status: "ok" } } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/health?full=1"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://internal-alb:8000/api/health/ready?full=1",
      {
        method: "GET",
        headers: { accept: "application/json" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("cache-control")).toBe("no-store");
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        status: "ok",
        checks: expect.objectContaining({
          database: expect.objectContaining({ status: "ok" }),
        }),
      }),
    );
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

  it("fails closed when the backend health route is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/health"));

    expect(response.status).toBe(503);
    expect(response.headers.get("cache-control")).toBe("no-store");
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        status: "not_ready",
        checks: expect.objectContaining({
          backend_proxy: expect.objectContaining({ status: "failed" }),
        }),
      }),
    );
  });

  it("returns structured 503 readiness failure when the backend is unreachable", async () => {
    process.env.APP_ENV = "dev";
    process.env.APP_RELEASE_VERSION = "1.2.3";
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED")));
    const { GET } = await import("./ready/route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/api/health/ready"));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({
        status: "not_ready",
        environment: "dev",
        release_version: "1.2.3",
        checks: expect.objectContaining({
          backend_proxy: expect.objectContaining({ status: "failed" }),
        }),
      }),
    );
  });
});
