import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { CopilotKitProviders, useThreadSession } from "./CopilotKitProviders";

const {
  usePathnameMock,
  randomUuidMock,
  copilotKitMountMock,
  copilotKitUnmountMock,
} = vi.hoisted(() => ({
  usePathnameMock: vi.fn<() => string>(() => "/agents/search"),
  randomUuidMock: vi.fn<() => string>(() => "12345678-1234-1234-1234-123456789abc"),
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
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.history.replaceState({}, "", "/agents/search");
    usePathnameMock.mockReturnValue("/agents/search");
    vi.spyOn(globalThis.crypto, "randomUUID").mockImplementation(randomUuidMock);
    copilotKitMountMock.mockReset();
    copilotKitUnmountMock.mockReset();
  });

  it("bootstraps the active thread from the URL and exposes it through the session context", async () => {
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
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-agent", "agent_search");
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-enable-inspector", "false");
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-show-dev-console", "false");
    expect(screen.getByTestId("copilotkit-root")).toHaveAttribute("data-thread-id", "url-thread");
  });

  it("creates a new thread, updates storage, and rewrites the thread URL param", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem("copilotkit_ui_active_thread_agent_search", "existing-thread");
    window.localStorage.setItem(
      "copilotkit_ui_thread_ids_agent_search",
      JSON.stringify(["existing-thread"]),
    );
    window.sessionStorage.setItem(
      "copilotkit_ui_resumable_thread_ids_tmp_agent_search",
      JSON.stringify(["existing-thread"]),
    );

    render(
      <CopilotKitProviders>
        <ThreadSessionConsumer />
      </CopilotKitProviders>,
    );

    await user.click(screen.getByRole("button", { name: "Create thread" }));

    await waitFor(() => {
      expect(screen.getByTestId("thread-id")).toHaveTextContent("agent_search-12345678");
    });

    expect(window.localStorage.getItem("copilotkit_ui_active_thread_agent_search")).toBe(
      "agent_search-12345678",
    );
    expect(window.sessionStorage.getItem("copilotkit_ui_resumable_thread_ids_tmp_agent_search")).toContain(
      "agent_search-12345678",
    );
    expect(window.location.search).toContain("room=room-dev-default");
    expect(window.location.search).toContain("thread=agent_search-12345678");
    expect(copilotKitUnmountMock).toHaveBeenCalledWith({
      agent: "agent_search",
      threadId: expect.any(String),
    });
    expect(copilotKitMountMock).toHaveBeenLastCalledWith({
      agent: "agent_search",
      threadId: "agent_search-12345678",
    });
  });

  it("shows a warning and keeps the current thread when selecting an unavailable backend thread", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(
      "copilotkit_ui_thread_ids_agent_search",
      JSON.stringify(["current-thread", "archived-thread"]),
    );
    window.localStorage.setItem("copilotkit_ui_active_thread_agent_search", "current-thread");
    window.sessionStorage.setItem(
      "copilotkit_ui_resumable_thread_ids_tmp_agent_search",
      JSON.stringify(["current-thread"]),
    );

    render(
      <CopilotKitProviders>
        <ThreadSessionConsumer />
      </CopilotKitProviders>,
    );

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
