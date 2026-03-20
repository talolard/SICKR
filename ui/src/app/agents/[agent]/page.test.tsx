import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { useEffect, useRef } from "react";
import { vi } from "vitest";

import AgentChatPage from "./page";
import type { AgentMetadata, AgentItem } from "@/lib/agents";
import type { AttachmentRef } from "@/lib/attachments";

const {
  useParamsMock,
  useRouterMock,
  routerPushMock,
  useThreadSessionMock,
  useAgentMock,
  useCopilotMessagesContextMock,
  fetchAgentsMock,
  fetchAgentMetadataMock,
  listThreadKnownFactsMock,
  listThreadBundleProposalsMock,
  loadThreadSnapshotMock,
  saveThreadSnapshotMock,
  loadFloorPlanPreviewMock,
  saveFloorPlanPreviewMock,
  setAgentStateMock,
  setMessagesMock,
  copilotToolRendererPropsMock,
} = vi.hoisted(() => ({
  useParamsMock: vi.fn<() => { agent: string }>(() => ({ agent: "search" })),
  routerPushMock: vi.fn(),
  useRouterMock: vi.fn(() => ({ push: routerPushMock })),
  useThreadSessionMock: vi.fn(),
  useAgentMock: vi.fn(),
  useCopilotMessagesContextMock: vi.fn(),
  fetchAgentsMock: vi.fn<() => Promise<AgentItem[]>>(),
  fetchAgentMetadataMock: vi.fn<(agent: string) => Promise<AgentMetadata>>(),
  listThreadKnownFactsMock: vi.fn<() => Promise<unknown[]>>(async () => []),
  listThreadBundleProposalsMock: vi.fn<() => Promise<unknown[]>>(async () => []),
  loadThreadSnapshotMock: vi.fn(),
  saveThreadSnapshotMock: vi.fn(),
  loadFloorPlanPreviewMock: vi.fn(() => null),
  saveFloorPlanPreviewMock: vi.fn(),
  setAgentStateMock: vi.fn(),
  setMessagesMock: vi.fn(),
  copilotToolRendererPropsMock: vi.fn(),
}));

vi.mock("next/dynamic", () => ({
  default: () =>
    function MockFloorPlanPreviewPanel({
      preview,
    }: {
      preview: { threadId: string; images: Array<{ uri: string }> } | null;
    }): ReactElement {
      return (
        <div data-testid="floor-plan-preview">
          {preview ? `${preview.threadId}:${preview.images[0]?.uri ?? "no-image"}` : "empty"}
        </div>
      );
    },
}));

vi.mock("next/navigation", () => ({
  useParams: useParamsMock,
  useRouter: useRouterMock,
}));

vi.mock("@copilotkit/react-core/v2", () => ({
  useAgent: useAgentMock,
}));

vi.mock("@copilotkit/react-core", () => ({
  useCopilotMessagesContext: useCopilotMessagesContextMock,
}));

vi.mock("@/app/CopilotKitProviders", () => ({
  useThreadSession: useThreadSessionMock,
}));

vi.mock("@/lib/agents", () => ({
  fetchAgents: fetchAgentsMock,
  fetchAgentMetadata: fetchAgentMetadataMock,
}));

vi.mock("@/lib/api/threadDataClient", () => ({
  listThreadKnownFacts: listThreadKnownFactsMock,
  listThreadBundleProposals: listThreadBundleProposalsMock,
  ThreadDataRequestError: class ThreadDataRequestError extends Error {
    status: number;

    constructor(status: number) {
      super(`status ${status}`);
      this.status = status;
    }
  },
}));

vi.mock("@/lib/threadStore", () => ({
  loadThreadSnapshot: loadThreadSnapshotMock,
  saveThreadSnapshot: saveThreadSnapshotMock,
}));

vi.mock("@/lib/floorPlanPreviewStore", () => ({
  loadFloorPlanPreview: loadFloorPlanPreviewMock,
  saveFloorPlanPreview: saveFloorPlanPreviewMock,
}));

vi.mock("@/components/agents/AgentInspectorPanel", () => ({
  AgentInspectorPanel: (): ReactElement => <div data-testid="agent-inspector-panel" />,
}));

vi.mock("@/components/navigation/AppNavBanner", () => ({
  AppNavBanner: (): ReactElement => <div data-testid="app-nav-banner" />,
}));

vi.mock("@/components/thread/ThreadDataPanel", () => ({
  ThreadDataPanel: ({ threadId }: { threadId: string }): ReactElement => (
    <div data-testid="thread-data-panel">{threadId}</div>
  ),
}));

vi.mock("@/components/search/SearchBundlePanel", () => ({
  SearchBundlePanel: (): ReactElement => <div data-testid="search-bundle-panel" />,
}));

vi.mock("@/components/copilotkit/AgentChatSidebar", () => ({
  AgentChatSidebar: (): ReactElement => <div data-testid="agent-chat-sidebar" />,
}));

vi.mock("@/components/attachments/AgentImageAttachmentPanel", () => ({
  AgentImageAttachmentPanel: ({
    helperText,
    onReadyAttachmentsChange,
  }: {
    helperText?: string;
    onReadyAttachmentsChange: (attachments: AttachmentRef[]) => void;
  }): ReactElement => {
    useEffect(() => {
      onReadyAttachmentsChange([
        {
          attachment_id: "att-1",
          mime_type: "image/png",
          uri: "floor-plan/preview.png",
          width: 1200,
          height: 800,
          file_name: "preview.png",
        },
      ]);
    }, [onReadyAttachmentsChange]);
    return <div data-testid="attachment-panel">{helperText ?? "attachments"}</div>;
  },
}));

vi.mock("@/components/copilotkit/CopilotToolRenderers", () => ({
  CopilotToolRenderers: ({
    threadId,
    onFloorPlanRendered,
  }: {
    threadId?: string | null;
    onFloorPlanRendered?: (snapshot: {
      caption: string;
      images: Array<{ uri: string }>;
      sceneRevision: number | null;
      sceneLevel: string | null;
      warnings: string[];
      legendItems: string[];
      scene: null;
      sceneSummary: null;
    }) => void;
  }): ReactElement => {
    const didPublishRef = useRef(false);
    copilotToolRendererPropsMock({ threadId });

    useEffect(() => {
      if (didPublishRef.current) {
        return;
      }
      didPublishRef.current = true;
      onFloorPlanRendered?.({
        caption: "Draft",
        images: [{ uri: "floor-plan/preview.png" }],
        sceneRevision: 2,
        sceneLevel: "detailed",
        warnings: [],
        legendItems: [],
        scene: null,
        sceneSummary: null,
      });
    }, [onFloorPlanRendered]);
    return <div data-testid="tool-renderers" />;
  },
}));

describe("AgentChatPage", () => {
  beforeEach(() => {
    fetchAgentsMock.mockResolvedValue([
      {
        name: "search",
        description: "Find products.",
        agent_key: "agent_search",
        ag_ui_path: "/ag-ui/agents/search",
      },
      {
        name: "floor_plan_intake",
        description: "Collect room layout constraints.",
        agent_key: "agent_floor_plan_intake",
        ag_ui_path: "/ag-ui/agents/floor_plan_intake",
      },
      {
        name: "image_analysis",
        description: "Review room photos.",
        agent_key: "agent_image_analysis",
        ag_ui_path: "/ag-ui/agents/image_analysis",
      },
    ]);
    fetchAgentMetadataMock.mockImplementation(async (agent) => ({
      name: agent,
      description: `metadata for ${agent}`,
      agent_key: `agent_${agent}`,
      ag_ui_path: `/ag-ui/agents/${agent}`,
      prompt_markdown: "",
      tools: [],
      notes: "",
    }));
    listThreadKnownFactsMock.mockResolvedValue([]);
    listThreadBundleProposalsMock.mockResolvedValue([]);
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_search",
      agentName: "search",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: "thread-1",
      threadIds: ["thread-1"],
      warning: null,
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });
    useAgentMock.mockReturnValue({
      agent: {
        state: { existing: true },
        setState: setAgentStateMock,
      },
    });
    useCopilotMessagesContextMock.mockReturnValue({
      messages: [{ id: "live-message" }],
      setMessages: setMessagesMock,
    });
    loadThreadSnapshotMock.mockReturnValue({
      threadId: "thread-1",
      prompt: "prompt",
      assistantText: "assistant",
      toolCallsById: {},
      attachments: [],
      copilotMessages: [{ id: "snapshot-message" }],
    });
    loadFloorPlanPreviewMock.mockReturnValue(null);
    setAgentStateMock.mockReset();
    setMessagesMock.mockReset();
    saveThreadSnapshotMock.mockReset();
    saveFloorPlanPreviewMock.mockReset();
    copilotToolRendererPropsMock.mockReset();
    routerPushMock.mockReset();
  });

  it("rehydrates thread messages and renders the search-specific shell without attachment panels", async () => {
    useParamsMock.mockReturnValue({ agent: "search" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_search",
      agentName: "search",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: "thread-1",
      threadIds: ["thread-1"],
      warning: null,
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });

    render(<AgentChatPage />);

    expect(await screen.findByTestId("search-bundle-panel")).toBeInTheDocument();
    expect(screen.getByTestId("agent-chat-sidebar")).toBeInTheDocument();
    expect(screen.queryByTestId("attachment-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("floor-plan-preview")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(setMessagesMock).toHaveBeenCalledWith([{ id: "snapshot-message" }]);
    });
    await waitFor(() => {
        expect(setAgentStateMock).toHaveBeenCalledWith(
          expect.objectContaining({
            existing: true,
            session_id: "session-browser",
            room_id: "room-dev-default",
            thread_id: "thread-1",
            attachments: [],
            bundle_proposals: [],
        }),
      );
    });
    expect(copilotToolRendererPropsMock).toHaveBeenCalledWith({ threadId: "thread-1" });
  });

  it("renders the floor-plan shell and wires uploaded attachments into the agent state", async () => {
    useParamsMock.mockReturnValue({ agent: "floor_plan_intake" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_floor_plan_intake",
      agentName: "floor_plan_intake",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: "thread-floor-plan",
      threadIds: ["thread-floor-plan"],
      warning: null,
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });

    render(<AgentChatPage />);

    expect(await screen.findByTestId("attachment-panel")).toHaveTextContent(
      "Uploaded images are added to floor-plan intake context for this thread.",
    );
    expect(screen.queryByTestId("search-bundle-panel")).not.toBeInTheDocument();

    await waitFor(() => {
        expect(setAgentStateMock).toHaveBeenCalledWith(
          expect.objectContaining({
            session_id: "session-browser",
            room_id: "room-dev-default",
            thread_id: "thread-floor-plan",
            attachments: [
              expect.objectContaining({
              attachment_id: "att-1",
              uri: "floor-plan/preview.png",
            }),
          ],
          bundle_proposals: [],
        }),
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("floor-plan-preview")).toHaveTextContent(
        "thread-floor-plan:/attachments/floor-plan/preview.png",
      );
    });
    expect(saveFloorPlanPreviewMock).toHaveBeenCalledWith(
      expect.objectContaining({
        threadId: "thread-floor-plan",
        images: [expect.objectContaining({ uri: "/attachments/floor-plan/preview.png" })],
      }),
    );
    expect(copilotToolRendererPropsMock).toHaveBeenCalledWith({
      threadId: "thread-floor-plan",
    });
  });

  it("keeps active-thread search chrome compact and hides the route description", async () => {
    useParamsMock.mockReturnValue({ agent: "search" });

    render(<AgentChatPage />);

    expect(await screen.findByRole("heading", { name: "Search" })).toBeInTheDocument();
    expect(screen.queryByText("Find products.")).not.toBeInTheDocument();
    expect(screen.getByText("Thread data")).toBeInTheDocument();
    expect(screen.getByText("Workbench")).toBeInTheDocument();
    expect(screen.getByText("Results")).toBeInTheDocument();

    const threadDataDetails = screen.getByText("Thread data").closest("details");
    expect(threadDataDetails).not.toHaveAttribute("open");
  });

  it("shows first-visit route guidance when no tracked thread exists", async () => {
    useParamsMock.mockReturnValue({ agent: "search" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_search",
      agentName: "search",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: null,
      threadIds: [],
      warning: null,
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });

    render(<AgentChatPage />);

    expect(
      await screen.findByText(
        "Curate products that solve the room brief without losing the design mood.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Thread data")).not.toBeInTheDocument();
    expect(screen.getByTestId("agent-thread-select")).toBeDisabled();
  });

  it("renders the image-analysis workspace with the compact empty-state board", async () => {
    useParamsMock.mockReturnValue({ agent: "image_analysis" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_image_analysis",
      agentName: "image_analysis",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: "thread-image",
      threadIds: ["thread-image"],
      warning: null,
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });

    render(<AgentChatPage />);

    expect(await screen.findByTestId("image-analysis-workspace-panel")).toBeInTheDocument();
    expect(screen.getByText("Visual context")).toBeInTheDocument();
    expect(screen.getByText("1 image ready")).toBeInTheDocument();
    expect(screen.getByText("Primary reference")).toBeInTheDocument();
    expect(screen.getByText("preview.png")).toBeInTheDocument();
  });

  it("renders warning state and dismiss affordance inside the route shell", async () => {
    useParamsMock.mockReturnValue({ agent: "search" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_search",
      agentName: "search",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: "thread-warning",
      threadIds: ["thread-warning"],
      warning: "archived-thread is not available",
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });

    render(<AgentChatPage />);

    expect(await screen.findByText("archived-thread is not available")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dismiss" })).toBeInTheDocument();
  });

  it("renders the unknown-agent fallback and routes home from the action", async () => {
    useParamsMock.mockReturnValue({ agent: "not_real" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_not_real",
      agentName: "not_real",
      roomId: "room-dev-default",
      sessionId: "session-browser",
      threadId: "thread-unknown",
      threadIds: ["thread-unknown"],
      warning: null,
      selectThread: vi.fn(),
      createThread: vi.fn(),
      clearWarning: vi.fn(),
    });

    render(<AgentChatPage />);

    expect(await screen.findByText("Unknown agent `not_real`.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Return home" }));

    expect(routerPushMock).toHaveBeenCalledWith("/");
  });
});
