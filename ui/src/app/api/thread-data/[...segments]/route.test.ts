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

describe("thread-data route", () => {
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
