"use client";

import type { ReactElement } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";

import { CopilotChatInlineError } from "@/components/copilotkit/CopilotChatInlineError";

export function AgentChatSidebar(): ReactElement {
  return (
    <CopilotSidebar
      renderError={({ message, onDismiss, onRetry, operation }) => (
        <CopilotChatInlineError
          message={message}
          onDismiss={onDismiss}
          onRetry={onRetry}
          operation={operation}
        />
      )}
    />
  );
}
