import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("attachment read route", () => {
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
