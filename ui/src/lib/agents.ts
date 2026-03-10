export type AgentItem = {
  name: string;
  description: string;
  agent_key: string;
  ag_ui_path: string;
};

export type AgentMetadata = {
  name: string;
  description: string;
  agent_key: string;
  ag_ui_path: string;
  prompt_markdown: string;
  tools: string[];
  notes: string;
};

export async function fetchAgents(): Promise<AgentItem[]> {
  const response = await fetch("/api/agents", { method: "GET" });
  if (!response.ok) {
    throw new Error(`Failed to fetch agents with status ${response.status}`);
  }
  const payload = (await response.json()) as { agents: AgentItem[] };
  return payload.agents;
}

export async function fetchAgentMetadata(agent: string): Promise<AgentMetadata> {
  const response = await fetch(`/api/agents/${agent}/metadata`, { method: "GET" });
  if (!response.ok) {
    throw new Error(`Failed to fetch agent metadata with status ${response.status}`);
  }
  return (await response.json()) as AgentMetadata;
}
