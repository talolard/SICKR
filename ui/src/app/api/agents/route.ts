import { NextRequest } from "next/server";

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

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(request: NextRequest): string {
  const baseUrl = new URL("../", agUiUrl);
  const upstream = new URL("api/agents", baseUrl);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }
  return upstream.toString();
}

export async function GET(request: NextRequest): Promise<Response> {
  try {
    const upstreamResponse = await fetch(buildUpstreamUrl(request), {
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
