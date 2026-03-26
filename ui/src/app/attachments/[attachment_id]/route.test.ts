import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const originalBackendProxyBaseUrl = process.env.BACKEND_PROXY_BASE_URL;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalBackendProxyBaseUrl === undefined) {
    delete process.env.BACKEND_PROXY_BASE_URL;
  } else {
    process.env.BACKEND_PROXY_BASE_URL = originalBackendProxyBaseUrl;
  }
});

describe("attachment read route", () => {
  it("uses the root ALB backend proxy base for deployed attachment reads", async () => {
    process.env.BACKEND_PROXY_BASE_URL = "http://internal-alb/";
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response("image-bytes", {
        status: 200,
        headers: {
          "content-type": "image/png",
          "cache-control": "private, max-age=120",
        },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://127.0.0.1:3000/attachments/asset-1"), {
      params: Promise.resolve({ attachment_id: "asset-1" }),
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [upstreamUrl, upstreamInit] = fetchSpy.mock.calls[0] ?? [];
    expect(String(upstreamUrl)).toBe("http://internal-alb/attachments/asset-1");
    expect(upstreamInit).toEqual({
      method: "GET",
    });
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("cache-control")).toBe("private, max-age=120");
  });

  it("logs and rethrows when the backend attachment read is unreachable", async () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("getaddrinfo ENOTFOUND")));
    const { GET } = await import("./route");

    await expect(
      GET(new NextRequest("http://127.0.0.1:3000/attachments/asset-1"), {
        params: Promise.resolve({ attachment_id: "asset-1" }),
      }),
    ).rejects.toThrow("getaddrinfo ENOTFOUND");

    const payload = JSON.parse(String(errorSpy.mock.calls[0]?.[0]));
    expect(payload).toMatchObject({
      event: "ui_attachment_read_upstream_unreachable",
      route: "/attachments/[attachment_id]",
      attachment_id: "asset-1",
      detail: "getaddrinfo ENOTFOUND",
    });
  });
});
