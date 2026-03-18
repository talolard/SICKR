import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { useEffect, useRef } from "react";
import { vi } from "vitest";

import AgentChatPage from "./page";
import type { AgentMetadata, AgentItem } from "@/lib/agents";
import type { AttachmentRef } from "@/lib/attachments";

const {
  useParamsMock,
  useRouterMock,
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
  useRouterMock: vi.fn(() => ({ push: vi.fn() })),
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

vi.mock("@/components/trace/SaveTraceButton", () => ({
  SaveTraceButton: (): ReactElement => <button type="button">Save trace</button>,
}));

vi.mock("@/components/trace/SaveTraceDialog", () => ({
  SaveTraceDialog: (): ReactElement => <div data-testid="save-trace-dialog" />,
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
  });

  it("rehydrates thread messages and renders the search-specific shell without attachment panels", async () => {
    useParamsMock.mockReturnValue({ agent: "search" });
    useThreadSessionMock.mockReturnValue({
      agentKey: "agent_search",
      agentName: "search",
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
          session_id: "thread-1",
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
});
