import { defineConfig } from "@playwright/test";

const uiPort = Number(process.env.UI_PORT ?? "3000");

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: `http://127.0.0.1:${uiPort}`,
    trace: "on-first-retry",
  },
  webServer: {
    command: `pnpm dev:mock --port ${uiPort}`,
    port: uiPort,
    reuseExistingServer: false,
  },
});
