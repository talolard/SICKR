import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { CopilotChatInlineError } from "./CopilotChatInlineError";

describe("CopilotChatInlineError", () => {
  it("announces request failures inline and wires retry and dismiss callbacks", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    const onRetry = vi.fn();

    render(
      <CopilotChatInlineError
        message="Gemini model lookup failed."
        onDismiss={onDismiss}
        onRetry={onRetry}
        operation="agent_run_failed"
      />,
    );

    expect(screen.getByRole("alert")).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText("This request failed.")).toBeInTheDocument();
    expect(screen.getByText("Gemini model lookup failed.")).toBeInTheDocument();
    expect(screen.getByText("Operation: agent_run_failed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));
    await user.click(screen.getByRole("button", { name: "Dismiss" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
