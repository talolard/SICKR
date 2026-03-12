import { defineConfig } from "@playwright/test";

const uiPort = Number(process.env.UI_PORT ?? "3000");

export default defineConfig({
  testDir: "./e2e",
  testMatch: /real-backend\.spec\.ts/,
  use: {
    baseURL: `http://127.0.0.1:${uiPort}`,
    trace: "on-first-retry",
  },
  webServer: {
    command: `pnpm dev --port ${uiPort}`,
    port: uiPort,
    reuseExistingServer: process.env.PLAYWRIGHT_REUSE_EXISTING_SERVER === "1",
  },
});
