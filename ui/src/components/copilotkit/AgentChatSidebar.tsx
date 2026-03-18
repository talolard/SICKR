"use client";

import type { ReactElement } from "react";
import { CopilotSidebar } from "@copilotkit/react-ui";

import { CopilotChatInlineError } from "@/components/copilotkit/CopilotChatInlineError";

function PersistentChatButton(): null {
  return null;
}

function PersistentChatHeader(): ReactElement {
  return (
    <div className="border-b border-gray-200 px-4 py-3">
      <p className="text-sm font-semibold text-gray-900">Chat</p>
    </div>
  );
}

export function AgentChatSidebar(): ReactElement {
  return (
    <CopilotSidebar
      Button={PersistentChatButton}
      Header={PersistentChatHeader}
      clickOutsideToClose={false}
      defaultOpen
      hitEscapeToClose={false}
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
