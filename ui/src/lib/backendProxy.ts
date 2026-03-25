function ensureTrailingSlash(value: string): string {
  return value.endsWith("/") ? value : `${value}/`;
}

function normalizeConfiguredUrl(value: string | undefined, fallback: string): string {
  const trimmed = value?.trim();
  if (!trimmed) {
    return fallback;
  }
  return ensureTrailingSlash(trimmed);
}

export function agUiBaseUrl(): string {
  return normalizeConfiguredUrl(process.env.PY_AG_UI_URL, "http://localhost:8000/ag-ui/");
}

export function backendProxyBaseUrl(): string {
  const explicit = process.env.BACKEND_PROXY_BASE_URL;
  if (explicit?.trim()) {
    return normalizeConfiguredUrl(explicit, "http://localhost:8000/");
  }

  const agUiUrl = new URL(agUiBaseUrl());
  const port =
    agUiUrl.port.length > 0 && agUiUrl.port !== "80" && agUiUrl.port !== "443"
      ? agUiUrl.port
      : "8000";
  agUiUrl.pathname = "/";
  agUiUrl.search = "";
  agUiUrl.hash = "";
  agUiUrl.port = port;
  return ensureTrailingSlash(agUiUrl.toString());
}

export function buildBackendProxyUrl(pathname: string, search = ""): URL {
  const upstream = new URL(pathname.replace(/^\//, ""), backendProxyBaseUrl());
  upstream.search = search;
  return upstream;
}

export function backendProxyLogFields(): Record<string, string> {
  return {
    ag_ui_base_url: agUiBaseUrl(),
    backend_proxy_base_url: backendProxyBaseUrl(),
  };
}
