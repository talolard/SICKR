import type { BundleProposal } from "@/lib/bundleProposalsStore";

export type ThreadDetailItem = {
  thread_id: string;
  title: string | null;
  room_id: string;
  room_title: string;
  room_type: string | null;
  status: string;
  last_activity_at: string | null;
  run_count: number;
  asset_count: number;
  floor_plan_revision_count: number;
  analysis_count: number;
  search_count: number;
};

export type ThreadListItem = {
  thread_id: string;
  room_id: string;
  title: string | null;
  status: string;
  last_activity_at: string | null;
};

export type AssetListItem = {
  asset_id: string;
  uri: string;
  run_id: string | null;
  created_by_tool: string | null;
  kind: string;
  display_label: string | null;
  mime_type: string;
  file_name: string | null;
  size_bytes: number;
  created_at: string | null;
};

export type KnownFactItem = {
  fact_id: string;
  scope: "project" | "room";
  kind: "constraint" | "fact" | "preference";
  summary: string;
  source_message_text: string;
  updated_at: string;
  run_id: string | null;
};

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

export type ThreadMessageItem = Record<string, unknown>;

export type ThreadTranscriptResponse = {
  room_id: string;
  thread_id: string;
  messages: ThreadMessageItem[];
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

function buildRoomThreadPath(roomId: string, threadId: string, suffix?: string): string {
  const basePath = `/api/thread-data/rooms/${roomId}/threads/${threadId}`;
  return suffix ? `${basePath}/${suffix}` : basePath;
}

function buildRoomThreadsPath(roomId: string): string {
  return `/api/thread-data/rooms/${roomId}/threads`;
}

export async function listRoomThreads(roomId: string): Promise<ThreadListItem[]> {
  return await readJson<ThreadListItem[]>(buildRoomThreadsPath(roomId));
}

export async function createRoomThread(
  roomId: string,
  title?: string | null,
): Promise<ThreadListItem> {
  return await readJson<ThreadListItem>(buildRoomThreadsPath(roomId), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(title ? { title } : {}),
  });
}

export async function getRoomThreadDetail(
  roomId: string,
  threadId: string,
): Promise<ThreadDetailItem> {
  return await readJson<ThreadDetailItem>(buildRoomThreadPath(roomId, threadId));
}

export async function listRoomThreadAssets(roomId: string, threadId: string): Promise<AssetListItem[]> {
  return await readJson<AssetListItem[]>(buildRoomThreadPath(roomId, threadId, "assets"));
}

export async function listRoomThreadBundleProposals(
  roomId: string,
  threadId: string,
): Promise<BundleProposal[]> {
  return await readJson<BundleProposal[]>(buildRoomThreadPath(roomId, threadId, "bundle-proposals"));
}

export async function listRoomThreadKnownFacts(
  roomId: string,
  threadId: string,
): Promise<KnownFactItem[]> {
  return await readJson<KnownFactItem[]>(buildRoomThreadPath(roomId, threadId, "known-facts"));
}

export async function listRoomThreadMessages(
  roomId: string,
  threadId: string,
): Promise<ThreadMessageItem[]> {
  const response = await readJson<ThreadTranscriptResponse>(
    buildRoomThreadPath(roomId, threadId, "messages"),
  );
  return response.messages;
}

export async function createRoomThreadAnalysisFeedback({
  roomId,
  threadId,
  analysisId,
  payload,
}: {
  roomId: string;
  threadId: string;
  analysisId: string;
  payload: AnalysisFeedbackCreateRequest;
}): Promise<AnalysisFeedbackItem> {
  return await readJson<AnalysisFeedbackItem>(
    buildRoomThreadPath(roomId, threadId, `analyses/${analysisId}/feedback`),
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}
