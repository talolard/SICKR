import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command: "pnpm dev:mock --port 3000",
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
