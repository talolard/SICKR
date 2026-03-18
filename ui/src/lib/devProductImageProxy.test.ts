import { describe, expect, it } from "vitest";

import {
  backendOriginFromAgUiUrl,
  buildDevProductImageRewrites,
} from "@/lib/devProductImageProxy";

describe("backendOriginFromAgUiUrl", () => {
  it("derives the backend origin from the AG-UI URL", () => {
    expect(backendOriginFromAgUiUrl("http://127.0.0.1:8126/ag-ui/")).toBe(
      "http://127.0.0.1:8126"
    );
  });

  it("returns null for invalid URLs", () => {
    expect(backendOriginFromAgUiUrl("not a url")).toBeNull();
  });
});

describe("buildDevProductImageRewrites", () => {
  it("returns a product image rewrite in development", () => {
    expect(
      buildDevProductImageRewrites({
        nodeEnv: "development",
        agUiUrl: "http://127.0.0.1:8126/ag-ui/",
      })
    ).toEqual([
      {
        source: "/static/product-images/:path*",
        destination: "http://127.0.0.1:8126/static/product-images/:path*",
      },
    ]);
  });

  it("does not add rewrites outside development", () => {
    expect(
      buildDevProductImageRewrites({
        nodeEnv: "production",
        agUiUrl: "http://127.0.0.1:8126/ag-ui/",
      })
    ).toEqual([]);
  });

  it("does not add rewrites when the AG-UI URL is missing", () => {
    expect(
      buildDevProductImageRewrites({
        nodeEnv: "development",
        agUiUrl: undefined,
      })
    ).toEqual([]);
  });
});
