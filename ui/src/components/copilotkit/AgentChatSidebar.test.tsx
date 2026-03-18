import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AgentChatSidebar } from "./AgentChatSidebar";

vi.mock("@copilotkit/react-ui", () => ({
  CopilotSidebar: ({
    Button,
    Header,
    clickOutsideToClose,
    defaultOpen,
    hitEscapeToClose,
    renderError,
  }: {
    Button?: () => React.ReactNode;
    Header?: () => React.ReactNode;
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
      <div data-testid="mock-sidebar-header">{Header ? Header() : "missing"}</div>
      {renderError({
        message: "Model request failed.",
        operation: "agent_run_failed",
        timestamp: 0,
        onDismiss: () => undefined,
        onRetry: () => undefined,
      })}
    </div>
  ),
}));

describe("AgentChatSidebar", () => {
  it("renders CopilotKit inline chat errors inside the sidebar", () => {
    render(<AgentChatSidebar />);

    expect(screen.getByTestId("mock-copilot-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("mock-sidebar-open")).toHaveTextContent("true");
    expect(screen.getByTestId("mock-sidebar-click-close")).toHaveTextContent("false");
    expect(screen.getByTestId("mock-sidebar-escape-close")).toHaveTextContent("false");
    expect(screen.getByTestId("mock-sidebar-button")).toHaveTextContent("true");
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("This request failed.")).toBeInTheDocument();
    expect(screen.getByText("Model request failed.")).toBeInTheDocument();
    expect(screen.getByText("Operation: agent_run_failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
