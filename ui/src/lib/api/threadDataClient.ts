import type { components } from "@/lib/api/generated";

export type ThreadDetailItem = components["schemas"]["ThreadDetailItem"];
export type AssetListItem = components["schemas"]["AssetListItem"];
export type AnalysisFeedbackKind = "confirm" | "reject" | "uncertain";

export type AnalysisFeedbackCreateRequest = {
  feedback_kind: AnalysisFeedbackKind;
  mask_ordinal?: number;
  mask_label?: string;
  query_text?: string;
  note?: string;
  run_id?: string;
};

export type AnalysisFeedbackItem = {
  analysis_feedback_id: string;
  analysis_id: string;
  thread_id: string;
  run_id: string | null;
  feedback_kind: AnalysisFeedbackKind;
  mask_ordinal: number | null;
  mask_label: string | null;
  query_text: string | null;
  note: string | null;
  created_at: string;
};

export class ThreadDataRequestError extends Error {
  status: number;

  constructor(status: number) {
    super(`Thread data request failed with status ${status}`);
    this.name = "ThreadDataRequestError";
    this.status = status;
  }
}

async function readJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new ThreadDataRequestError(response.status);
  }
  return (await response.json()) as T;
}

export async function getThreadDetail(threadId: string): Promise<ThreadDetailItem> {
  return await readJson<ThreadDetailItem>(`/api/thread-data/threads/${threadId}`);
}

export async function listThreadAssets(threadId: string): Promise<AssetListItem[]> {
  return await readJson<AssetListItem[]>(`/api/thread-data/threads/${threadId}/assets`);
}

export async function createAnalysisFeedback({
  threadId,
  analysisId,
  payload,
}: {
  threadId: string;
  analysisId: string;
  payload: AnalysisFeedbackCreateRequest;
}): Promise<AnalysisFeedbackItem> {
  return await readJson<AnalysisFeedbackItem>(
    `/api/thread-data/threads/${threadId}/analyses/${analysisId}/feedback`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}
