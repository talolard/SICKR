import { NextRequest } from "next/server";

import { backendProxyLogFields, buildBackendProxyUrl } from "@/lib/backendProxy";
import {
  getMockAgentMetadata,
  mockBackendFallbacksEnabled,
} from "@/lib/mockBackendFallbacks";
import { logServerRouteEvent } from "@/lib/serverRouteLogging";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ agent: string }> },
): Promise<Response> {
  const { agent } = await context.params;
  const upstream = buildBackendProxyUrl(
    `/api/agents/${agent}/metadata`,
    request.nextUrl.search,
  ).toString();

  try {
    const upstreamResponse = await fetch(upstream, {
      method: "GET",
      headers: { accept: "application/json" },
    });

    const body = await upstreamResponse.text();
    return new Response(body, {
      status: upstreamResponse.status,
      headers: { "content-type": "application/json" },
    });
  } catch (error) {
    logServerRouteEvent("error", "ui_agent_metadata_proxy_failed", {
      agent,
      detail: error instanceof Error ? error.message : "Unknown backend agent metadata failure.",
      route: "/api/agents/[agent]/metadata",
      upstream_url: upstream,
      ...backendProxyLogFields(),
    });
    if (!mockBackendFallbacksEnabled()) {
      throw error;
    }
    const fallback = getMockAgentMetadata(agent);
    if (!fallback) {
      return new Response(JSON.stringify({ error: "Unknown mock agent." }), {
        status: 404,
        headers: { "content-type": "application/json" },
      });
    }
    return new Response(JSON.stringify(fallback), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }
}
