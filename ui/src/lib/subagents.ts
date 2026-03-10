export type SubagentItem = {
  name: string;
  description: string;
  agent_key: string;
  ag_ui_path: string;
};

export type SubagentMetadata = {
  name: string;
  description: string;
  agent_key: string;
  ag_ui_path: string;
  prompt_markdown: string;
  tools: string[];
  notes: string;
};

export async function fetchSubagents(): Promise<SubagentItem[]> {
  const response = await fetch("/api/subagents", { method: "GET" });
  if (!response.ok) {
    throw new Error(`Failed to fetch subagents with status ${response.status}`);
  }
  const payload = (await response.json()) as { subagents: SubagentItem[] };
  return payload.subagents;
}

export async function fetchSubagentMetadata(agent: string): Promise<SubagentMetadata> {
  const response = await fetch(`/api/subagents/${agent}/metadata`, { method: "GET" });
  if (!response.ok) {
    throw new Error(`Failed to fetch subagent metadata with status ${response.status}`);
  }
  return (await response.json()) as SubagentMetadata;
}
