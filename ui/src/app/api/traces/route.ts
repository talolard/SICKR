import { NextRequest } from "next/server";

import { buildBackendProxyUrl } from "@/lib/backendProxy";

const traceDisabledMessage =
  "Trace capture is unavailable. Enable TRACE_CAPTURE_ENABLED on the backend or hide the UI flag.";

function buildUpstreamUrl(pathname: string, search: string): URL {
  const upstream = buildBackendProxyUrl(pathname, search);
  upstream.search = search;
  return upstream;
}

async function proxyTraceRequest(
  request: NextRequest,
  pathname: string,
  method: "POST",
): Promise<Response> {
  const upstream = buildUpstreamUrl(pathname, request.nextUrl.search);
  const upstreamResponse = await fetch(upstream, {
    method,
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
    },
    ...(method === "POST" ? { body: await request.text() } : {}),
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

export async function POST(request: NextRequest): Promise<Response> {
  return proxyTraceRequest(request, "../api/traces", "POST");
}
