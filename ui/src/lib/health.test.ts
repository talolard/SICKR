import { afterEach, describe, expect, it, vi } from "vitest";

import { getHealthStatus } from "./health";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("getHealthStatus", () => {
  it("uses MSW handler response", async () => {
    await expect(getHealthStatus()).resolves.toEqual({ status: "ok" });
  });

  it("calls the local health route without caching", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchSpy);

    await getHealthStatus();

    expect(fetchSpy).toHaveBeenCalledWith(expect.stringMatching(/\/api\/health$/), {
      cache: "no-store",
    });
  });

  it("raises when the health route returns a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("bad gateway", { status: 502 })),
    );

    await expect(getHealthStatus()).rejects.toThrow("Health request failed: 502");
  });
});
