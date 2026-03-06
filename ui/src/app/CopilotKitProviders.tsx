"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactElement, ReactNode } from "react";
import { CopilotKit } from "@copilotkit/react-core";

import {
  loadActiveThreadId,
  loadResumableThreadIds,
  loadThreadIds,
  saveActiveThreadId,
  saveResumableThreadIds,
  upsertThreadId,
} from "@/lib/threadStore";

type CopilotKitProvidersProps = {
  children: ReactNode;
};

type ThreadSessionContextValue = {
  threadId: string | null;
  threadIds: string[];
  warning: string | null;
  selectThread: (threadId: string) => void;
  createThread: () => void;
  clearWarning: () => void;
};

const ThreadSessionContext = createContext<ThreadSessionContextValue | null>(null);

function randomThreadId(): string {
  return crypto.randomUUID().slice(0, 8);
}

function setUrlThread(threadId: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("thread", threadId);
  window.history.replaceState({}, "", url.toString());
}

export function CopilotKitProviders({
  children,
}: CopilotKitProvidersProps): ReactElement {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [threadIds, setThreadIds] = useState<string[]>([]);
  const [resumableThreadIds, setResumableThreadIds] = useState<string[]>([]);
  const [warning, setWarning] = useState<string | null>(null);

  const replaceThreadIds = useCallback((nextThreadIds: string[]): void => {
    setThreadIds(nextThreadIds);
  }, []);

  const replaceResumableThreadIds = useCallback((nextThreadIds: string[]): void => {
    setResumableThreadIds(nextThreadIds);
  }, []);

  const activateThread = useCallback((nextThreadId: string): void => {
    setThreadId(nextThreadId);
    saveActiveThreadId(nextThreadId);
    const updatedThreadIds = upsertThreadId(nextThreadId);
    setThreadIds(updatedThreadIds);
    setUrlThread(nextThreadId);
  }, []);

  const markResumable = useCallback((nextThreadId: string): void => {
    setResumableThreadIds((current) => {
      if (current.includes(nextThreadId)) {
        return current;
      }
      const next = [nextThreadId, ...current];
      saveResumableThreadIds(next);
      return next;
    });
  }, []);

  const createThread = useCallback((): void => {
    const nextThreadId = randomThreadId();
    activateThread(nextThreadId);
    markResumable(nextThreadId);
    setWarning(null);
  }, [activateThread, markResumable]);

  const selectThread = useCallback(
    (requestedThreadId: string): void => {
      if (!threadId || requestedThreadId === threadId) {
        setWarning(null);
        return;
      }
      if (resumableThreadIds.includes(requestedThreadId)) {
        activateThread(requestedThreadId);
        setWarning(null);
        return;
      }
      const nextThreadId = randomThreadId();
      activateThread(nextThreadId);
      markResumable(nextThreadId);
      setWarning(
        `Temporary limitation: thread ${requestedThreadId} is not available on the backend. Started new thread ${nextThreadId}.`,
      );
    },
    [activateThread, markResumable, resumableThreadIds, threadId],
  );

  useEffect(() => {
    const url = new URL(window.location.href);
    const threadFromUrl = url.searchParams.get("thread");
    const threadFromStorage = loadActiveThreadId();
    const resolvedThreadId = threadFromUrl ?? threadFromStorage ?? randomThreadId();
    const indexedThreadIds = loadThreadIds();
    const restoredResumable = loadResumableThreadIds();

    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time bootstrap from URL/storage.
    replaceThreadIds(
      indexedThreadIds.includes(resolvedThreadId)
        ? indexedThreadIds
        : [resolvedThreadId, ...indexedThreadIds],
    );
    activateThread(resolvedThreadId);
    const nextResumable = restoredResumable.includes(resolvedThreadId)
      ? restoredResumable
      : [resolvedThreadId, ...restoredResumable];
    saveResumableThreadIds(nextResumable);
    replaceResumableThreadIds(nextResumable);
  }, [activateThread, replaceResumableThreadIds, replaceThreadIds]);

  const contextValue = useMemo<ThreadSessionContextValue>(
    () => ({
      threadId,
      threadIds,
      warning,
      selectThread,
      createThread,
      clearWarning: () => setWarning(null),
    }),
    [createThread, selectThread, threadId, threadIds, warning],
  );

  return (
    <ThreadSessionContext.Provider value={contextValue}>
      <CopilotKit runtimeUrl="/api/copilotkit" agent="ikea_agent" threadId={threadId ?? undefined}>
        {children}
      </CopilotKit>
    </ThreadSessionContext.Provider>
  );
}

export function useThreadSession(): ThreadSessionContextValue {
  const value = useContext(ThreadSessionContext);
  if (!value) {
    throw new Error("useThreadSession must be used within CopilotKitProviders.");
  }
  return value;
}
