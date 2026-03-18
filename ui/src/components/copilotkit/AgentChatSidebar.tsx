"use client";

import type { ReactElement } from "react";
import { CopilotChat } from "@copilotkit/react-ui";

import { CopilotChatInlineError } from "@/components/copilotkit/CopilotChatInlineError";

export function AgentChatSidebar(): ReactElement {
  return (
    <section className="flex h-full min-h-[60vh] min-w-0 flex-col overflow-hidden rounded border border-gray-200 bg-white">
      <div className="border-b border-gray-200 px-4 py-3">
        <p className="text-sm font-semibold text-gray-900">Chat</p>
      </div>
      <CopilotChat
        className="min-h-0 flex-1"
        renderError={({ message, onDismiss, onRetry, operation }) => (
          <CopilotChatInlineError
            message={message}
            onDismiss={onDismiss}
            onRetry={onRetry}
            operation={operation}
          />
        )}
      />
    </section>
  );
}
