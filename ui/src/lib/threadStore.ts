import type { PendingAttachment } from "@/lib/attachments";
import type { ToolCallEntry } from "@/lib/toolEvents";

type ThreadSnapshot = {
  threadId: string;
  prompt: string;
  assistantText: string;
  toolCallsById: Record<string, ToolCallEntry>;
  attachments: PendingAttachment[];
  messages?: Array<{
    id: string;
    role: "user" | "assistant";
    text: string;
    toolCallIds: string[];
  }>;
};

const ACTIVE_THREAD_KEY = "copilotkit_ui_active_thread";
const THREAD_PREFIX = "copilotkit_ui_thread_";
const THREAD_IDS_KEY = "copilotkit_ui_thread_ids";
const RESUMABLE_THREAD_IDS_KEY = "copilotkit_ui_resumable_thread_ids_tmp";

function threadKey(threadId: string): string {
  return `${THREAD_PREFIX}${threadId}`;
}

export function loadActiveThreadId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(ACTIVE_THREAD_KEY);
}

export function saveActiveThreadId(threadId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(ACTIVE_THREAD_KEY, threadId);
}

export function loadThreadSnapshot(threadId: string): ThreadSnapshot | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(threadKey(threadId));
  if (!raw) {
    return null;
  }
  return JSON.parse(raw) as ThreadSnapshot;
}

export function saveThreadSnapshot(snapshot: ThreadSnapshot): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(threadKey(snapshot.threadId), JSON.stringify(snapshot));
}

export function loadThreadIds(): string[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(THREAD_IDS_KEY);
  if (!raw) {
    return [];
  }
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    return [];
  }
  return parsed.filter((value): value is string => typeof value === "string");
}

export function saveThreadIds(threadIds: string[]): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(THREAD_IDS_KEY, JSON.stringify(threadIds));
}

export function upsertThreadId(threadId: string): string[] {
  const current = loadThreadIds();
  if (current.includes(threadId)) {
    return current;
  }
  const next = [threadId, ...current];
  saveThreadIds(next);
  return next;
}

export function loadResumableThreadIds(): string[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.sessionStorage.getItem(RESUMABLE_THREAD_IDS_KEY);
  if (!raw) {
    return [];
  }
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) {
    return [];
  }
  return parsed.filter((value): value is string => typeof value === "string");
}

export function saveResumableThreadIds(threadIds: string[]): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(RESUMABLE_THREAD_IDS_KEY, JSON.stringify(threadIds));
}

export type { ThreadSnapshot };
