import { NextRequest, NextResponse } from "next/server";

import { backendProxyLogFields, buildBackendProxyUrl } from "@/lib/backendProxy";
import { logServerRouteEvent, runtimeMetadata } from "@/lib/serverRouteLogging";

function cacheControlHeaders(contentType = "application/json"): HeadersInit {
  return {
    "cache-control": "no-store",
    "content-type": contentType,
  };
}

export function liveHealthResponse(): Response {
  return NextResponse.json(
    {
      status: "ok",
      checks: {
        ui: {
          status: "ok",
          detail: "Next.js route handler is serving requests.",
        },
      },
      ...runtimeMetadata(),
    },
    {
      status: 200,
      headers: cacheControlHeaders(),
    },
  );
}

export async function proxyReadyHealth(request: NextRequest): Promise<Response> {
  const upstreamUrl = buildBackendProxyUrl("/api/health/ready", request.nextUrl.search).toString();
  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    const text = await upstreamResponse.text();
    if (!upstreamResponse.ok) {
      logServerRouteEvent("error", "ui_ready_health_upstream_failed", {
        route: "/api/health/ready",
        status_code: upstreamResponse.status,
        upstream_url: upstreamUrl,
        ...backendProxyLogFields(),
      });
    }
    return new Response(text, {
      status: upstreamResponse.status,
      headers: cacheControlHeaders(
        upstreamResponse.headers.get("content-type") ?? "application/json",
      ),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown upstream health failure.";
    logServerRouteEvent("error", "ui_ready_health_upstream_unreachable", {
      detail: message,
      route: "/api/health/ready",
      upstream_url: upstreamUrl,
      ...backendProxyLogFields(),
    });
    return NextResponse.json(
      {
        status: "not_ready",
        checks: {
          backend_proxy: {
            status: "failed",
            detail: message,
          },
        },
        ...runtimeMetadata(),
      },
      {
        status: 503,
        headers: cacheControlHeaders(),
      },
    );
  }
}
