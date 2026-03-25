import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, vi } from "vitest";

import { CopilotKitProviders, useThreadSession } from "./CopilotKitProviders";

const { usePathnameMock, copilotKitMountMock, copilotKitUnmountMock } = vi.hoisted(() => ({
  usePathnameMock: vi.fn<() => string>(() => "/agents/search"),
  copilotKitMountMock: vi.fn(),
  copilotKitUnmountMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
}));

vi.mock("@copilotkit/react-core", () => ({
  CopilotKit: ({
    agent,
    children,
    enableInspector,
    runtimeUrl,
    showDevConsole,
    threadId,
  }: {
    agent: string;
    children: ReactElement;
    enableInspector?: boolean;
    runtimeUrl: string;
    showDevConsole?: boolean;
    threadId?: string;
  }): ReactElement => {
    React.useEffect(() => {
      copilotKitMountMock({ agent, threadId: threadId ?? "" });
      return () => {
        copilotKitUnmountMock({ agent, threadId: threadId ?? "" });
      };
    }, [agent, threadId]);

    return (
      <div
        data-agent={agent}
        data-enable-inspector={String(enableInspector)}
        data-runtime-url={runtimeUrl}
        data-show-dev-console={String(showDevConsole)}
        data-testid="copilotkit-root"
        data-thread-id={threadId ?? ""}
      >
        {children}
      </div>
    );
  },
}));

function jsonResponse(body: unknown, status: number = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function ThreadSessionConsumer(): ReactElement {
  const { agentKey, roomId, sessionId, threadId, threadIds, warning, createThread, selectThread } =
    useThreadSession();

  return (
    <div>
      <p data-testid="agent-key">{agentKey}</p>
      <p data-testid="room-id">{roomId}</p>
      <p data-testid="session-id">{sessionId}</p>
      <p data-testid="thread-id">{threadId ?? "none"}</p>
      <p data-testid="thread-ids">{threadIds.join(",")}</p>
      <p data-testid="warning">{warning ?? "none"}</p>
      <button onClick={createThread} type="button">
        Create thread
      </button>
      <button
        onClick={() => {
          selectThread("archived-thread");
        }}
        type="button"
      >
        Select archived thread
      </button>
    </div>
  );
}

describe("CopilotKitProviders", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.history.replaceState({}, "", "/agents/search");
    usePathnameMock.mockReturnValue("/agents/search");
    copilotKitMountMock.mockReset();
    copilotKitUnmountMock.mockReset();
  });

  it("bootstraps the active thread from the URL and exposes it through the session context", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("/api/thread-data/rooms/room-url/threads");
      expect(init).toBeUndefined();
      return jsonResponse([
        {
          thread_id: "url-thread",
          room_id: "room-url",
          title: null,
          status: "active",
          last_activity_at: "2026-03-20T09:00:00Z",
        },
      ]);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/agents/search?room=room-url&thread=url-thread");
    window.localStorage.setItem("copilotkit_ui_active_thread_agent_search", "stored-thread");

    render(
      <CopilotKitProviders>
        <ThreadSessionConsumer />
      </CopilotKitProviders>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("url-thread");
    });

    expect(screen.getByTestId("agent-key")).toHaveTextContent("agent_search");
    expect(screen.getByTestId("room-id")).toHaveTextContent("room-url");
    expect(screen.getByTestId("session-id")).not.toHaveTextContent("none");
    expect(screen.getByTestId("thread-ids")).toHaveTextContent("url-thread");
    expect(window.localStorage.getItem("copilotkit_ui_active_thread_agent_search")).toBe(
      "url-thread",
    );
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-agent", "agent_search");
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-enable-inspector", "false");
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-show-dev-console", "false");
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-thread-id", "url-thread");
  });

  it("creates a backend thread when the requested URL thread is missing", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (String(input) === "/api/thread-data/rooms/room-dev-default/threads" && method === "GET") {
        return jsonResponse([]);
      }
      if (String(input) === "/api/thread-data/rooms/room-dev-default/threads" && method === "POST") {
        return jsonResponse(
          {
            thread_id: "thread-created",
            room_id: "room-dev-default",
            title: null,
            status: "active",
            last_activity_at: "2026-03-20T09:05:00Z",
          },
          201,
        );
      }
      throw new Error(`Unexpected request: ${method} ${String(input)}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState(
      {},
      "",
      "/agents/search?room=room-dev-default&thread=missing-thread",
    );

    render(
      <CopilotKitProviders>
        <ThreadSessionConsumer />
      </CopilotKitProviders>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("thread-created");
    });

    expect(window.localStorage.getItem("copilotkit_ui_active_thread_agent_search")).toBe(
      "thread-created",
    );
    expect(screen.getByTestId("warning")).toHaveTextContent(
      "Thread missing-thread is not available for room room-dev-default. Created a new thread instead.",
    );
    expect(window.location.search).toContain("room=room-dev-default");
    expect(window.location.search).toContain("thread=thread-created");
    expect(copilotKitUnmountMock).toHaveBeenCalledWith({
      agent: "agent_search",
      threadId: expect.any(String),
    });
    expect(copilotKitMountMock).toHaveBeenLastCalledWith({
      agent: "agent_search",
      threadId: "thread-created",
    });
  });

  it("creates a new backend thread on explicit user request", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (String(input) === "/api/thread-data/rooms/room-dev-default/threads" && method === "GET") {
        return jsonResponse([
          {
            thread_id: "current-thread",
            room_id: "room-dev-default",
            title: null,
            status: "active",
            last_activity_at: "2026-03-20T09:00:00Z",
          },
        ]);
      }
      if (String(input) === "/api/thread-data/rooms/room-dev-default/threads" && method === "POST") {
        return jsonResponse(
          {
            thread_id: "thread-created",
            room_id: "room-dev-default",
            title: null,
            status: "active",
            last_activity_at: "2026-03-20T09:10:00Z",
          },
          201,
        );
      }
      throw new Error(`Unexpected request: ${method} ${String(input)}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.setItem("copilotkit_ui_active_thread_agent_search", "current-thread");

    render(
      <CopilotKitProviders>
        <ThreadSessionConsumer />
      </CopilotKitProviders>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("current-thread");
    });

    await user.click(screen.getByRole("button", { name: "Create thread" }));

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("thread-created");
    });

    expect(screen.getByTestId("thread-ids")).toHaveTextContent(
      "thread-created,current-thread",
    );
    expect(window.localStorage.getItem("copilotkit_ui_active_thread_agent_search")).toBe(
      "thread-created",
    );
    expect(window.location.search).toContain("thread=thread-created");
  });

  it("shows a warning and keeps the current thread when selecting an unavailable backend thread", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe("/api/thread-data/rooms/room-dev-default/threads");
      expect(init).toBeUndefined();
      return jsonResponse([
        {
          thread_id: "current-thread",
          room_id: "room-dev-default",
          title: null,
          status: "active",
          last_activity_at: "2026-03-20T09:00:00Z",
        },
      ]);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.localStorage.setItem("copilotkit_ui_active_thread_agent_search", "current-thread");

    render(
      <CopilotKitProviders>
        <ThreadSessionConsumer />
      </CopilotKitProviders>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("current-thread");
    });

    await user.click(screen.getByRole("button", { name: "Select archived thread" }));

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("current-thread");
    });

    expect(screen.getByTestId("warning")).toHaveTextContent(
      "Thread archived-thread is not available for room room-dev-default.",
    );
    expect(window.localStorage.getItem("copilotkit_ui_active_thread_agent_search")).toBe(
      "current-thread",
    );
  });
});
