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
    <>
      <style jsx global>{`
        .copilotKitSidebarContentWrapper {
          display: flex;
          min-height: 100%;
          width: 100%;
          overflow: hidden;
          margin-right: 0;
        }

        .copilotKitSidebarContentWrapper.sidebarExpanded {
          margin-right: 0;
        }

        .agent-chat-sidebar.copilotKitSidebar {
          position: static;
          right: auto;
          bottom: auto;
          z-index: auto;
          display: flex;
          min-height: 100%;
          width: 100%;
        }

        .agent-chat-sidebar.copilotKitSidebar .copilotKitWindow {
          position: static;
          inset: auto;
          display: flex;
          width: 100%;
          min-height: 60vh;
          height: 100%;
          max-height: none;
          margin-bottom: 0;
          border-radius: 0.5rem;
          border: 1px solid rgb(229 231 235);
          box-shadow: none;
          opacity: 1;
          transform: none;
          pointer-events: auto;
        }

        .agent-chat-sidebar.copilotKitSidebar .copilotKitWindow.open {
          transform: none;
        }
      `}</style>
      <CopilotSidebar
        Button={PersistentChatButton}
        Header={PersistentChatHeader}
        className="agent-chat-sidebar"
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
    </>
  );
}
