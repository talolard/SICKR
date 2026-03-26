import { afterEach, describe, expect, it } from "vitest";

import { agUiBaseUrl, backendProxyBaseUrl, buildBackendProxyUrl } from "./backendProxy";

const originalAgUiUrl = process.env.PY_AG_UI_URL;
const originalBackendProxyBaseUrl = process.env.BACKEND_PROXY_BASE_URL;

afterEach(() => {
  if (originalAgUiUrl === undefined) {
    delete process.env.PY_AG_UI_URL;
  } else {
    process.env.PY_AG_UI_URL = originalAgUiUrl;
  }

  if (originalBackendProxyBaseUrl === undefined) {
    delete process.env.BACKEND_PROXY_BASE_URL;
  } else {
    process.env.BACKEND_PROXY_BASE_URL = originalBackendProxyBaseUrl;
  }
});

describe("backendProxy", () => {
  it("keeps the AG-UI base URL separate from the backend proxy base URL", () => {
    process.env.PY_AG_UI_URL = "http://example-alb/ag-ui/";
    delete process.env.BACKEND_PROXY_BASE_URL;

    expect(agUiBaseUrl()).toBe("http://example-alb/ag-ui/");
    expect(backendProxyBaseUrl()).toBe("http://example-alb/");
    expect(buildBackendProxyUrl("/api/agents", "?full=1").toString()).toBe(
      "http://example-alb/api/agents?full=1",
    );
  });

  it("prefers an explicit backend proxy base URL when configured", () => {
    process.env.PY_AG_UI_URL = "http://example-alb/ag-ui/";
    process.env.BACKEND_PROXY_BASE_URL = "http://internal-alb:9000";

    expect(backendProxyBaseUrl()).toBe("http://internal-alb:9000/");
  });
});
