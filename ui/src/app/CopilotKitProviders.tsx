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
  saveThreadIdsForAgent,
  upsertThreadId,
} from "@/lib/threadStore";
import { getOrCreateSessionId } from "@/lib/sessionStore";

type CopilotKitProvidersProps = {
  children: ReactNode;
};

type ThreadSessionContextValue = {
  agentKey: string;
  agentName: string | null;
  roomId: string;
  sessionId: string;
  threadId: string | null;
  threadIds: string[];
  warning: string | null;
  selectThread: (threadId: string) => void;
  createThread: () => void;
  clearWarning: () => void;
};

type ThreadBootstrapState = {
  roomId: string;
  sessionId: string;
  threadId: string | null;
  threadIds: string[];
  resumableThreadIds: string[];
};

const ThreadSessionContext = createContext<ThreadSessionContextValue | null>(null);
const DEFAULT_ROOM_ID = "room-dev-default";

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

function setUrlContext(threadId: string, roomId: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("room", roomId);
  url.searchParams.set("thread", threadId);
  window.history.replaceState({}, "", url.toString());
}

function readThreadBootstrapState(agentKey: string): ThreadBootstrapState {
  if (typeof window === "undefined") {
    return {
      roomId: DEFAULT_ROOM_ID,
      sessionId: "",
      threadId: null,
      threadIds: [],
      resumableThreadIds: [],
    };
  }

  const url = new URL(window.location.href);
  const roomId = url.searchParams.get("room") ?? DEFAULT_ROOM_ID;
  const threadFromUrl = url.searchParams.get("thread");
  const threadFromStorage = loadActiveThreadId(agentKey);
  const threadId = threadFromUrl ?? threadFromStorage ?? randomThreadId(agentKey);
  const storedThreadIds = loadThreadIds(agentKey);
  const threadIds = storedThreadIds.includes(threadId)
    ? storedThreadIds
    : [threadId, ...storedThreadIds];
  const storedResumableThreadIds = loadResumableThreadIds(agentKey);
  const resumableThreadIds = storedResumableThreadIds.includes(threadId)
    ? storedResumableThreadIds
    : [threadId, ...storedResumableThreadIds];

  return {
    roomId,
    sessionId: getOrCreateSessionId(window.sessionStorage),
    threadId,
    threadIds,
    resumableThreadIds,
  };
}

type AgentSessionProviderProps = CopilotKitProvidersProps & {
  agentKey: string;
  agentName: string | null;
};

function AgentSessionProvider({
  agentKey,
  agentName,
  children,
}: AgentSessionProviderProps): ReactElement {
  const [bootstrapState, setBootstrapState] = useState<ThreadBootstrapState>(() =>
    readThreadBootstrapState(agentKey),
  );
  const { roomId, sessionId, threadId, threadIds, resumableThreadIds } = bootstrapState;
  const [warning, setWarning] = useState<string | null>(null);

  const activateThread = useCallback((nextThreadId: string, nextRoomId?: string): void => {
    const resolvedRoomId = nextRoomId ?? roomId;
    saveActiveThreadId(nextThreadId, agentKey);
    const updatedThreadIds = upsertThreadId(nextThreadId, agentKey);
    setBootstrapState((current) => ({
      ...current,
      roomId: resolvedRoomId,
      threadId: nextThreadId,
      threadIds: updatedThreadIds,
    }));
    setUrlContext(nextThreadId, resolvedRoomId);
  }, [agentKey, roomId]);

  const markResumable = useCallback((nextThreadId: string): void => {
    setBootstrapState((current) => {
      if (current.resumableThreadIds.includes(nextThreadId)) {
        return current;
      }
      const next = [nextThreadId, ...current.resumableThreadIds];
      saveResumableThreadIds(next, agentKey);
      return {
        ...current,
        resumableThreadIds: next,
      };
    });
  }, [agentKey]);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    saveActiveThreadId(threadId, agentKey);
    saveThreadIdsForAgent(threadIds, agentKey);
    saveResumableThreadIds(resumableThreadIds, agentKey);
    setUrlContext(threadId, roomId);
  }, [agentKey, resumableThreadIds, roomId, threadId, threadIds]);

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
      setWarning(
        `Thread ${requestedThreadId} is not available for room ${roomId}. Select an existing thread or create a new one.`,
      );
    },
    [activateThread, roomId, resumableThreadIds, threadId],
  );

  const contextValue = useMemo<ThreadSessionContextValue>(
    () => ({
      agentKey,
      agentName,
      roomId,
      sessionId,
      threadId,
      threadIds,
      warning,
      selectThread,
      createThread,
      clearWarning: () => setWarning(null),
    }),
    [agentKey, agentName, createThread, roomId, selectThread, sessionId, threadId, threadIds, warning],
  );
  const copilotBoundaryKey = threadId
    ? `${agentKey}:${roomId}:${threadId}`
    : `${agentKey}:${roomId}:pending`;

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

export function CopilotKitProviders({
  children,
}: CopilotKitProvidersProps): ReactElement {
  const pathname = usePathname();
  const { agentKey, agentName } = useMemo(() => resolveAgentContext(pathname), [pathname]);

  return (
    <AgentSessionProvider key={agentKey} agentKey={agentKey} agentName={agentName}>
      {children}
    </AgentSessionProvider>
  );
}

export function useThreadSession(): ThreadSessionContextValue {
  const value = useContext(ThreadSessionContext);
  if (!value) {
    throw new Error("useThreadSession must be used within CopilotKitProviders.");
  }
  return value;
}
