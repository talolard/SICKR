import type { PendingAttachment } from "@/lib/attachments";
import type { ToolCallEntry } from "@/lib/toolEvents";

type ThreadSnapshot = {
  threadId: string;
  prompt: string;
  assistantText: string;
  toolCallsById: Record<string, ToolCallEntry>;
  attachments: PendingAttachment[];
};

const ACTIVE_THREAD_KEY = "copilotkit_ui_active_thread";
const THREAD_PREFIX = "copilotkit_ui_thread_";

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

export type { ThreadSnapshot };
