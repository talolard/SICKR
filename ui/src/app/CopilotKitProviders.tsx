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
import { usePathname } from "next/navigation";

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
  agentKey: string;
  agentName: string | null;
  threadId: string | null;
  threadIds: string[];
  warning: string | null;
  selectThread: (threadId: string) => void;
  createThread: () => void;
  clearWarning: () => void;
};

const ThreadSessionContext = createContext<ThreadSessionContextValue | null>(null);

function resolveAgentContext(pathname: string): { agentKey: string; agentName: string | null } {
  const match = pathname.match(/^\/agents\/([^/]+)/);
  if (match && match[1]) {
    return { agentKey: `agent_${match[1]}`, agentName: match[1] };
  }
  // Home defaults to floor_plan_intake key even without active chat.
  return { agentKey: "agent_floor_plan_intake", agentName: null };
}

function randomThreadId(agentKey: string): string {
  return `${agentKey.replace(/[^a-z0-9_]/gi, "").slice(0, 20)}-${crypto.randomUUID().slice(0, 8)}`;
}

function setUrlThread(threadId: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("thread", threadId);
  window.history.replaceState({}, "", url.toString());
}

export function CopilotKitProviders({
  children,
}: CopilotKitProvidersProps): ReactElement {
  const pathname = usePathname();
  const { agentKey, agentName } = useMemo(() => resolveAgentContext(pathname), [pathname]);
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
    saveActiveThreadId(nextThreadId, agentKey);
    const updatedThreadIds = upsertThreadId(nextThreadId, agentKey);
    setThreadIds(updatedThreadIds);
    setUrlThread(nextThreadId);
  }, [agentKey]);

  const markResumable = useCallback((nextThreadId: string): void => {
    setResumableThreadIds((current) => {
      if (current.includes(nextThreadId)) {
        return current;
      }
      const next = [nextThreadId, ...current];
      saveResumableThreadIds(next, agentKey);
      return next;
    });
  }, [agentKey]);

  const createThread = useCallback((): void => {
    const nextThreadId = randomThreadId(agentKey);
    activateThread(nextThreadId);
    markResumable(nextThreadId);
    setWarning(null);
  }, [activateThread, agentKey, markResumable]);

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
      const nextThreadId = randomThreadId(agentKey);
      activateThread(nextThreadId);
      markResumable(nextThreadId);
      setWarning(
        `Temporary limitation: thread ${requestedThreadId} is not available on the backend. Started new thread ${nextThreadId}.`,
      );
    },
    [activateThread, agentKey, markResumable, resumableThreadIds, threadId],
  );

  useEffect(() => {
    const url = new URL(window.location.href);
    const threadFromUrl = url.searchParams.get("thread");
    const threadFromStorage = loadActiveThreadId(agentKey);
    const resolvedThreadId = threadFromUrl ?? threadFromStorage ?? randomThreadId(agentKey);
    const indexedThreadIds = loadThreadIds(agentKey);
    const restoredResumable = loadResumableThreadIds(agentKey);

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
    saveResumableThreadIds(nextResumable, agentKey);
    replaceResumableThreadIds(nextResumable);
  }, [activateThread, agentKey, replaceResumableThreadIds, replaceThreadIds]);

  const contextValue = useMemo<ThreadSessionContextValue>(
    () => ({
      agentKey,
      agentName,
      threadId,
      threadIds,
      warning,
      selectThread,
      createThread,
      clearWarning: () => setWarning(null),
    }),
    [agentKey, agentName, createThread, selectThread, threadId, threadIds, warning],
  );
  const copilotBoundaryKey = threadId ? `${agentKey}:${threadId}` : `${agentKey}:pending`;

  return (
    <ThreadSessionContext.Provider value={contextValue}>
      <CopilotKit
        key={copilotBoundaryKey}
        agent={agentKey}
        enableInspector={false}
        runtimeUrl="/api/copilotkit"
        showDevConsole={false}
        {...(threadId ? { threadId } : {})}
      >
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
