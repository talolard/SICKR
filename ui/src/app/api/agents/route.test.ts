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

describe("agents route", () => {
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
