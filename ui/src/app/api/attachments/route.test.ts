import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const originalMockFlag = process.env.NEXT_PUBLIC_USE_MOCK_AGENT;

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalMockFlag === undefined) {
    delete process.env.NEXT_PUBLIC_USE_MOCK_AGENT;
  } else {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = originalMockFlag;
  }
});

describe("attachment upload route", () => {
  it("logs failed upstream responses and preserves the status code", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "0";
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "bad upstream" }), {
        status: 503,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchSpy);
    const { POST } = await import("./route");

    const response = await POST(
      new NextRequest("http://127.0.0.1:3000/api/attachments", {
        method: "POST",
        body: new Uint8Array([1, 2, 3]),
        headers: {
          "content-type": "image/png",
          "x-room-id": "room-1",
          "x-thread-id": "thread-1",
          "x-run-id": "run-1",
          "x-filename": "chair.png",
        },
      }),
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: "bad upstream" });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const payload = JSON.parse(String(errorSpy.mock.calls[0]?.[0]));
    expect(payload).toMatchObject({
      event: "ui_attachment_upload_failed",
      route: "/api/attachments",
      room_id: "room-1",
      run_id: "run-1",
      status_code: 503,
      thread_id: "thread-1",
    });
  });

  it("logs and rethrows when the backend upload call is unreachable", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AGENT = "0";
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ETIMEDOUT")));
    const { POST } = await import("./route");

    await expect(
      POST(
        new NextRequest("http://127.0.0.1:3000/api/attachments", {
          method: "POST",
          body: new Uint8Array([1, 2, 3]),
          headers: {
            "content-type": "image/png",
            "x-thread-id": "thread-1",
            "x-run-id": "run-1",
          },
        }),
      ),
    ).rejects.toThrow("connect ETIMEDOUT");

    const payload = JSON.parse(String(errorSpy.mock.calls[0]?.[0]));
    expect(payload).toMatchObject({
      event: "ui_attachment_upload_upstream_unreachable",
      route: "/api/attachments",
      run_id: "run-1",
      thread_id: "thread-1",
      detail: "connect ETIMEDOUT",
    });
  });
});
