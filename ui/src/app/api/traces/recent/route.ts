import { NextRequest } from "next/server";

import { buildBackendProxyUrl } from "@/lib/backendProxy";

const traceDisabledMessage =
  "Trace capture is unavailable. Enable TRACE_CAPTURE_ENABLED on the backend or hide the UI flag.";

function buildUpstreamUrl(pathname: string, search: string): URL {
  const upstream = buildBackendProxyUrl(pathname, search);
  upstream.search = search;
  return upstream;
}

export async function GET(request: NextRequest): Promise<Response> {
  const upstream = buildUpstreamUrl("/api/traces/recent", request.nextUrl.search);
  const upstreamResponse = await fetch(upstream, {
    method: "GET",
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
    },
  });
  const body = await upstreamResponse.text();
  if (upstreamResponse.status === 404) {
    return new Response(traceDisabledMessage, {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  return new Response(body, {
    status: upstreamResponse.status,
    headers: {
      "content-type": upstreamResponse.headers.get("content-type") ?? "application/json",
    },
  });
}
