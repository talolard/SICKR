import type { components } from "@/lib/api/generated";

export type ThreadDetailItem = components["schemas"]["ThreadDetailItem"];
export type AssetListItem = components["schemas"]["AssetListItem"];

async function readJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(`Thread data request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function getThreadDetail(threadId: string): Promise<ThreadDetailItem> {
  return await readJson<ThreadDetailItem>(`/api/thread-data/threads/${threadId}`);
}

export async function listThreadAssets(threadId: string): Promise<AssetListItem[]> {
  return await readJson<AssetListItem[]>(`/api/thread-data/threads/${threadId}/assets`);
}
