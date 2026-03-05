import { getHealthStatus } from "./health";

describe("getHealthStatus", () => {
  it("uses MSW handler response", async () => {
    await expect(getHealthStatus()).resolves.toEqual({ status: "ok" });
  });
});
