import { NextRequest } from "next/server";

import { backendProxyLogFields, buildBackendProxyUrl } from "@/lib/backendProxy";
import { listMockAgentItems, mockBackendFallbacksEnabled } from "@/lib/mockBackendFallbacks";
import { logServerRouteEvent } from "@/lib/serverRouteLogging";

type AgentItem = {
  name: string;
  description: string;
  agent_key: string;
  ag_ui_path: string;
};

type AgentListResponse = {
  agents: AgentItem[];
};

function buildUpstreamUrl(request: NextRequest): URL {
  return buildBackendProxyUrl("/api/agents", request.nextUrl.search);
}

export async function GET(request: NextRequest): Promise<Response> {
  const upstreamUrl = buildUpstreamUrl(request).toString();
  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: "GET",
      headers: { accept: "application/json" },
    });

    const payload = (await upstreamResponse.json()) as AgentListResponse;
    const shaped = {
      agents: payload.agents,
    };

    return new Response(JSON.stringify(shaped), {
      status: upstreamResponse.status,
      headers: { "content-type": "application/json" },
    });
  } catch (error) {
    logServerRouteEvent("error", "ui_agents_proxy_failed", {
      detail: error instanceof Error ? error.message : "Unknown backend agents failure.",
      route: "/api/agents",
      upstream_url: upstreamUrl,
      ...backendProxyLogFields(),
    });
    if (!mockBackendFallbacksEnabled()) {
      throw error;
    }
    return new Response(JSON.stringify({ agents: listMockAgentItems() }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }
}
