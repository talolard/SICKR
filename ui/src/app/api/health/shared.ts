import { NextRequest, NextResponse } from "next/server";

import { logServerRouteEvent, runtimeMetadata } from "@/lib/serverRouteLogging";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(request: NextRequest, backendPath: string): string {
  const baseUrl = new URL("../", agUiUrl);
  const upstream = new URL(backendPath.replace(/^\//, ""), baseUrl);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }
  return upstream.toString();
}

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
  const upstreamUrl = buildUpstreamUrl(request, "/api/health/ready");
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
