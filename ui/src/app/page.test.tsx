import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { beforeEach, vi } from "vitest";

import Home from "./page";

type ThreadSessionState = {
  threadId: string | null;
  threadIds: string[];
  warning: string | null;
};

const sidebarProps: Array<Record<string, unknown>> = [];

const mockAgent = {
  state: {},
  setState: vi.fn(),
};

let currentThreadSession: ThreadSessionState = {
  threadId: null,
  threadIds: [],
  warning: null,
};

vi.mock("@copilotkit/react-core/v2", () => ({
  CopilotSidebar: (props: Record<string, unknown>): ReactElement => {
    sidebarProps.push(props);
    return <div data-testid="copilot-sidebar" />;
  },
  useAgent: () => ({ agent: mockAgent }),
}));

vi.mock("@/app/CopilotKitProviders", () => ({
  useThreadSession: () => ({
    ...currentThreadSession,
    selectThread: vi.fn(),
    createThread: vi.fn(),
    clearWarning: vi.fn(),
  }),
}));

vi.mock("@/components/attachments/AttachmentComposer", () => ({
  AttachmentComposer: (): ReactElement => <div data-testid="attachment-composer" />,
}));

vi.mock("@/components/copilotkit/CopilotToolRenderers", () => ({
  CopilotToolRenderers: (): ReactElement => <div data-testid="tool-renderers" />,
}));

vi.mock("@/components/thread/ThreadDataPanel", () => ({
  ThreadDataPanel: (): ReactElement => <div data-testid="thread-data-panel" />,
}));

vi.mock("@/components/tooling/FloorPlanPreviewPanel", () => ({
  FloorPlanPreviewPanel: (): ReactElement => <div data-testid="floor-plan-preview-panel" />,
}));

vi.mock("@/lib/floorPlanPreviewEvents", () => ({
  subscribeFloorPlanRendered: vi.fn(() => () => undefined),
}));

vi.mock("@/lib/floorPlanPreviewStore", () => ({
  loadFloorPlanPreview: vi.fn(() => null),
  saveFloorPlanPreview: vi.fn(),
}));

vi.mock("@/lib/api/room3dClient", () => ({
  createRoom3DSnapshot: vi.fn(),
}));

vi.mock("@/lib/threadStore", () => ({
  loadRoom3DSnapshots: vi.fn(() => []),
  saveRoom3DSnapshots: vi.fn(),
}));

vi.mock("@/lib/feedbackCapture", () => ({
  getConsoleRecordsSnapshot: vi.fn(() => []),
  startFeedbackCapture: vi.fn(),
}));

describe("Home page", () => {
  beforeEach(() => {
    sidebarProps.length = 0;
    mockAgent.setState.mockReset();
    currentThreadSession = {
      threadId: null,
      threadIds: [],
      warning: null,
    };
  });

  it("passes a stable agentId to CopilotSidebar across rerenders", () => {
    const { rerender } = render(<Home />);

    currentThreadSession = {
      threadId: "900339f6",
      threadIds: ["900339f6"],
      warning: null,
    };
    rerender(<Home />);

    expect(sidebarProps.length).toBeGreaterThanOrEqual(2);
    expect(sidebarProps[0]?.agentId).toBe("ikea_agent");
    expect(sidebarProps[1]?.agentId).toBe("ikea_agent");
    expect(sidebarProps[0]?.threadId).toBeUndefined();
    expect(sidebarProps[1]?.threadId).toBe("900339f6");
  });
});
