import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AgentChatSidebar } from "./AgentChatSidebar";

vi.mock("@copilotkit/react-ui", () => ({
  CopilotSidebar: ({
    renderError,
  }: {
    renderError: (error: {
      message: string;
      operation?: string;
      timestamp: number;
      onDismiss: () => void;
      onRetry?: () => void;
    }) => React.ReactNode;
  }) => (
    <div data-testid="mock-copilot-sidebar">
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
    expect(screen.getByText("This request failed.")).toBeInTheDocument();
    expect(screen.getByText("Model request failed.")).toBeInTheDocument();
    expect(screen.getByText("Operation: agent_run_failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
