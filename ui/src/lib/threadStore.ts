import type { PendingAttachment } from "@/lib/attachments";
import type { AttachmentRef } from "@/lib/attachments";
import type { ToolCallEntry } from "@/lib/toolEvents";

export type Room3DSnapshotContext = {
  snapshot_id: string;
  attachment: AttachmentRef;
  comment: string | null;
  captured_at: string;
  camera: {
    position_m: [number, number, number];
    target_m: [number, number, number];
    fov_deg: number;
  };
  lighting: {
    light_fixture_ids: string[];
    emphasized_light_count: number;
  };
};

type ThreadSnapshot = {
  threadId: string;
  prompt: string;
  assistantText: string;
  toolCallsById: Record<string, ToolCallEntry>;
  attachments: PendingAttachment[];
  copilotMessages?: unknown[];
  messages?: Array<{
    id: string;
    role: "user" | "assistant";
    text: string;
    toolCallIds: string[];
  }>;
};

const ACTIVE_THREAD_KEY = "copilotkit_ui_active_thread";
const THREAD_PREFIX = "copilotkit_ui_thread_";
const ROOM_3D_SNAPSHOT_PREFIX = "copilotkit_ui_room3d_snapshots_";
const DEFAULT_AGENT_KEY = "agent_floor_plan_intake";

function scopedKey(baseKey: string, agentKey: string): string {
  return `${baseKey}_${agentKey}`;
}

function threadKey(agentKey: string, threadId: string): string {
  return `${THREAD_PREFIX}${agentKey}_${threadId}`;
}

export function loadActiveThreadId(agentKey: string = DEFAULT_AGENT_KEY): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(scopedKey(ACTIVE_THREAD_KEY, agentKey));
}

export function saveActiveThreadId(
  threadId: string,
  agentKey: string = DEFAULT_AGENT_KEY,
): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(scopedKey(ACTIVE_THREAD_KEY, agentKey), threadId);
}

export function loadThreadSnapshot(
  threadId: string,
  agentKey: string = DEFAULT_AGENT_KEY,
): ThreadSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(threadKey(agentKey, threadId));
  if (!raw) {
    return null;
  }
  return JSON.parse(raw) as ThreadSnapshot;
}

export function saveThreadSnapshot(
  snapshot: ThreadSnapshot,
  agentKey: string = DEFAULT_AGENT_KEY,
): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(threadKey(agentKey, snapshot.threadId), JSON.stringify(snapshot));
}

function room3dSnapshotKey(agentKey: string, threadId: string): string {
  return `${ROOM_3D_SNAPSHOT_PREFIX}${agentKey}_${threadId}`;
}

export function loadRoom3DSnapshots(
  threadId: string,
  agentKey: string = DEFAULT_AGENT_KEY,
): Room3DSnapshotContext[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(room3dSnapshotKey(agentKey, threadId));
  if (!raw) {
    return [];
  }
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    return [];
  }
  return parsed.filter(
    (value): value is Room3DSnapshotContext =>
      typeof value === "object" &&
      value !== null &&
      "snapshot_id" in value &&
      "attachment" in value,
  );
}

export function saveRoom3DSnapshots(
  threadId: string,
  snapshots: Room3DSnapshotContext[],
  agentKey: string = DEFAULT_AGENT_KEY,
): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(room3dSnapshotKey(agentKey, threadId), JSON.stringify(snapshots));
}

export type { ThreadSnapshot };
