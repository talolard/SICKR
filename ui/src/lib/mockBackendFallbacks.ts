import type { AgentItem, AgentMetadata } from "@/lib/agents";

const MOCK_AGENT_ITEMS: AgentItem[] = [
  {
    name: "search",
    description: "Find products.",
    agent_key: "agent_search",
    ag_ui_path: "/ag-ui/agents/search",
  },
  {
    name: "floor_plan_intake",
    description: "Collect room layout constraints.",
    agent_key: "agent_floor_plan_intake",
    ag_ui_path: "/ag-ui/agents/floor_plan_intake",
  },
  {
    name: "image_analysis",
    description: "Review uploaded room images.",
    agent_key: "agent_image_analysis",
    ag_ui_path: "/ag-ui/agents/image_analysis",
  },
];

const MOCK_AGENT_METADATA: Record<string, AgentMetadata> = {
  search: {
    name: "search",
    description: "Find products.",
    agent_key: "agent_search",
    ag_ui_path: "/ag-ui/agents/search",
    prompt_markdown: "",
    tools: [],
    notes: "Mock fallback metadata.",
  },
  floor_plan_intake: {
    name: "floor_plan_intake",
    description: "Collect room layout constraints.",
    agent_key: "agent_floor_plan_intake",
    ag_ui_path: "/ag-ui/agents/floor_plan_intake",
    prompt_markdown: "",
    tools: [],
    notes: "Mock fallback metadata.",
  },
  image_analysis: {
    name: "image_analysis",
    description: "Review uploaded room images.",
    agent_key: "agent_image_analysis",
    ag_ui_path: "/ag-ui/agents/image_analysis",
    prompt_markdown: "",
    tools: [],
    notes: "Mock fallback metadata.",
  },
};

export function mockBackendFallbacksEnabled(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK_AGENT === "1";
}

export function listMockAgentItems(): AgentItem[] {
  return MOCK_AGENT_ITEMS;
}

export function getMockAgentMetadata(agent: string): AgentMetadata | null {
  return MOCK_AGENT_METADATA[agent] ?? null;
}
