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

import { createRoomThread, listRoomThreads } from "@/lib/api/threadDataClient";
import {
  loadActiveThreadId,
  saveActiveThreadId,
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
  preferredThreadId: string | null;
};

type ThreadState = {
  threadId: string | null;
  threadIds: string[];
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

function setUrlContext(threadId: string, roomId: string): void {
  const url = new URL(window.location.href);
  url.searchParams.set("room", roomId);
  url.searchParams.set("thread", threadId);
  window.history.replaceState({}, "", url.toString());
}

function orderThreadIds(selectedThreadId: string, threadIds: string[]): string[] {
  return [selectedThreadId, ...threadIds.filter((threadId) => threadId !== selectedThreadId)];
}

function readThreadBootstrapState(agentKey: string): ThreadBootstrapState {
  if (typeof window === "undefined") {
    return {
      roomId: DEFAULT_ROOM_ID,
      sessionId: "",
      preferredThreadId: null,
    };
  }

  const url = new URL(window.location.href);
  const roomId = url.searchParams.get("room") ?? DEFAULT_ROOM_ID;
  const preferredThreadId = url.searchParams.get("thread") ?? loadActiveThreadId(agentKey);

  return {
    roomId,
    sessionId: getOrCreateSessionId(window.sessionStorage),
    preferredThreadId,
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
  const [bootstrapState] = useState<ThreadBootstrapState>(() =>
    readThreadBootstrapState(agentKey),
  );
  const [threadState, setThreadState] = useState<ThreadState>({
    threadId: null,
    threadIds: [],
  });
  const [warning, setWarning] = useState<string | null>(null);
  const { roomId, sessionId, preferredThreadId } = bootstrapState;
  const { threadId, threadIds } = threadState;

  const activateThread = useCallback((nextThreadId: string, nextThreadIds?: string[]): void => {
    saveActiveThreadId(nextThreadId, agentKey);
    setThreadState((current) => ({
      threadId: nextThreadId,
      threadIds: orderThreadIds(nextThreadId, nextThreadIds ?? current.threadIds),
    }));
    setUrlContext(nextThreadId, roomId);
  }, [agentKey, roomId]);

  useEffect(() => {
    let active = true;

    async function bootstrapThreads(): Promise<void> {
      try {
        const roomThreads = await listRoomThreads(roomId);
        if (!active) {
          return;
        }
        const availableThreadIds = roomThreads.map((thread) => thread.thread_id);

        if (preferredThreadId && availableThreadIds.includes(preferredThreadId)) {
          activateThread(preferredThreadId, availableThreadIds);
          setWarning(null);
          return;
        }

        if (availableThreadIds.length > 0) {
          const fallbackThreadId = availableThreadIds[0] ?? null;
          if (!fallbackThreadId) {
            return;
          }
          activateThread(fallbackThreadId, availableThreadIds);
          setWarning(
            preferredThreadId
              ? `Thread ${preferredThreadId} is not available for room ${roomId}. Switched to ${fallbackThreadId}.`
              : null,
          );
          return;
        }

        const createdThread = await createRoomThread(roomId);
        if (!active) {
          return;
        }
        activateThread(createdThread.thread_id, [createdThread.thread_id]);
        setWarning(
          preferredThreadId
            ? `Thread ${preferredThreadId} is not available for room ${roomId}. Created a new thread instead.`
            : null,
        );
      } catch (error) {
        if (!active) {
          return;
        }
        setWarning(error instanceof Error ? error.message : "Failed to load room threads.");
      }
    }

    void bootstrapThreads();
    return () => {
      active = false;
    };
  }, [activateThread, preferredThreadId, roomId]);

  const createThread = useCallback((): void => {
    void createRoomThread(roomId)
      .then((createdThread) => {
        activateThread(createdThread.thread_id);
        setWarning(null);
      })
      .catch((error: unknown) => {
        setWarning(error instanceof Error ? error.message : "Failed to create thread.");
      });
  }, [activateThread, roomId]);

  const selectThread = useCallback(
    (requestedThreadId: string): void => {
      if (!threadId || requestedThreadId === threadId) {
        setWarning(null);
        return;
      }
      if (threadIds.includes(requestedThreadId)) {
        activateThread(requestedThreadId);
        setWarning(null);
        return;
      }
      setWarning(
        `Thread ${requestedThreadId} is not available for room ${roomId}. Select an existing thread or create a new one.`,
      );
    },
    [activateThread, roomId, threadId, threadIds],
  );

  const clearWarning = useCallback((): void => {
    setWarning(null);
  }, []);

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
      clearWarning,
    }),
    [
      agentKey,
      agentName,
      clearWarning,
      createThread,
      roomId,
      selectThread,
      sessionId,
      threadId,
      threadIds,
      warning,
    ],
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
