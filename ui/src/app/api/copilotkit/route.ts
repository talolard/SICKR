import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();
const baseAgUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui";
const MAIN_AGENT_KEY = "ikea_agent";

type SubagentCatalogItem = {
  name?: string;
  agent_key?: string;
  ag_ui_path?: string;
};

type SubagentCatalogResponse = {
  subagents?: SubagentCatalogItem[];
};

function normalizedAgUiBase(): string {
  return baseAgUiUrl.endsWith("/") ? baseAgUiUrl.slice(0, -1) : baseAgUiUrl;
}

function backendBaseUrl(): string {
  return new URL("../", `${normalizedAgUiBase()}/`).toString();
}

function resolveAgUiUrl(agentKey: string): string {
  const normalizedBase = normalizedAgUiBase();
  if (agentKey.startsWith("subagent_")) {
    const subagentName = agentKey.slice("subagent_".length);
    return `${normalizedBase}/subagents/${subagentName}`;
  }
  return normalizedBase;
}

function resolveSubagentAgentKey(item: SubagentCatalogItem): string | null {
  if (typeof item.agent_key === "string" && item.agent_key.length > 0) {
    return item.agent_key;
  }
  if (typeof item.name === "string" && item.name.length > 0) {
    return `subagent_${item.name}`;
  }
  return null;
}

function resolveSubagentAgUiUrl(item: SubagentCatalogItem): string | null {
  if (typeof item.ag_ui_path === "string" && item.ag_ui_path.startsWith("/")) {
    return new URL(item.ag_ui_path, backendBaseUrl()).toString();
  }
  if (typeof item.name === "string" && item.name.length > 0) {
    return `${normalizedAgUiBase()}/subagents/${item.name}`;
  }
  return null;
}

async function fetchSubagentCatalog(): Promise<SubagentCatalogItem[]> {
  const url = new URL("api/subagents", backendBaseUrl());
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return [];
    }
    const payload = (await response.json()) as SubagentCatalogResponse;
    return Array.isArray(payload.subagents) ? payload.subagents : [];
  } catch {
    return [];
  }
}

async function buildAgentMap(selectedAgent: string): Promise<Record<string, HttpAgent>> {
  const agents: Record<string, HttpAgent> = {
    [MAIN_AGENT_KEY]: new HttpAgent({ url: resolveAgUiUrl(MAIN_AGENT_KEY) }),
  };

  const subagents = await fetchSubagentCatalog();
  for (const item of subagents) {
    const agentKey = resolveSubagentAgentKey(item);
    if (!agentKey || agentKey in agents) {
      continue;
    }
    const url = resolveSubagentAgUiUrl(item) ?? resolveAgUiUrl(agentKey);
    agents[agentKey] = new HttpAgent({ url });
  }

  if (!(selectedAgent in agents)) {
    agents[selectedAgent] = new HttpAgent({ url: resolveAgUiUrl(selectedAgent) });
  }

  return agents;
}

export const POST = async (request: NextRequest): Promise<Response> => {
  const requestedAgent = request.nextUrl.searchParams.get("agent");
  const selectedAgent = requestedAgent && requestedAgent.length > 0 ? requestedAgent : MAIN_AGENT_KEY;
  const agents = await buildAgentMap(selectedAgent);
  const runtime = new CopilotRuntime({
    agents,
  });
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(request);
};
