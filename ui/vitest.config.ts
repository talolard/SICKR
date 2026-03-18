import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      // @ts-expect-error Vitest accepts `all` at runtime, but the local type surface omits it.
      all: true,
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.d.ts",
        "src/**/__mocks__/**",
        "src/**/playwright*.{ts,tsx}",
      ],
      reporter: ["text", "lcov", "json-summary"],
    },
  },
});
