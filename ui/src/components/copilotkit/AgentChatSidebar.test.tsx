import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AgentChatSidebar } from "./AgentChatSidebar";

const useChatContextMock = vi.fn(() => ({ open: true }));

vi.mock("@copilotkit/react-ui", () => ({
  CopilotSidebar: ({
    Button,
    Header,
    Window,
    clickOutsideToClose,
    defaultOpen,
    hitEscapeToClose,
    renderError,
  }: {
    Button?: () => React.ReactNode;
    Header?: () => React.ReactNode;
    Window?: (props: { children: React.ReactNode }) => React.ReactNode;
    clickOutsideToClose?: boolean;
    defaultOpen?: boolean;
    hitEscapeToClose?: boolean;
    renderError: (error: {
      message: string;
      operation?: string;
      timestamp: number;
      onDismiss: () => void;
      onRetry?: () => void;
    }) => React.ReactNode;
  }) => (
    <div data-testid="mock-copilot-sidebar">
      <div data-testid="mock-sidebar-open">{String(defaultOpen)}</div>
      <div data-testid="mock-sidebar-click-close">{String(clickOutsideToClose)}</div>
      <div data-testid="mock-sidebar-escape-close">{String(hitEscapeToClose)}</div>
      <div data-testid="mock-sidebar-button">{Button ? String(Button() === null) : "missing"}</div>
      <div data-testid="mock-sidebar-window">
        {Window
          ? Window({
              children: (
                <>
                  {Header ? Header() : null}
                  <div data-testid="mock-sidebar-chat-body">sidebar-body</div>
                  {renderError({
                    message: "Model request failed.",
                    operation: "agent_run_failed",
                    timestamp: 0,
                    onDismiss: () => undefined,
                    onRetry: () => undefined,
                  })}
                </>
              ),
            })
          : "missing"}
      </div>
    </div>
  ),
  useChatContext: () => useChatContextMock(),
}));

describe("AgentChatSidebar", () => {
  it("renders the richer CopilotKit sidebar shell inside an inline window", () => {
    render(<AgentChatSidebar />);

    expect(screen.getByTestId("mock-copilot-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("mock-sidebar-open")).toHaveTextContent("true");
    expect(screen.getByTestId("mock-sidebar-click-close")).toHaveTextContent("false");
    expect(screen.getByTestId("mock-sidebar-escape-close")).toHaveTextContent("false");
    expect(screen.getByTestId("mock-sidebar-button")).toHaveTextContent("true");
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByTestId("mock-sidebar-chat-body")).toBeInTheDocument();
    expect(screen.getByText("This request failed.")).toBeInTheDocument();
    expect(screen.getByText("Model request failed.")).toBeInTheDocument();
    expect(screen.getByText("Operation: agent_run_failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("hides the inline window when the CopilotKit sidebar is closed", () => {
    useChatContextMock.mockReturnValueOnce({ open: false });

    render(<AgentChatSidebar />);

    expect(screen.getByTestId("mock-sidebar-window")).toBeEmptyDOMElement();
  });
});
