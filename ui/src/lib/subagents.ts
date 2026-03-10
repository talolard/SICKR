export type SubagentItem = {
  name: string;
  description: string;
  web_path: string;
  chat_proxy_path: string;
  chat_url: string;
};

export async function fetchSubagents(): Promise<SubagentItem[]> {
  const response = await fetch("/api/subagents", { method: "GET" });
  if (!response.ok) {
    throw new Error(`Failed to fetch subagents with status ${response.status}`);
  }
  const payload = (await response.json()) as { subagents: SubagentItem[] };
  return payload.subagents;
}
