"use client";

import type { ReactElement } from "react";
import { CopilotChat } from "@copilotkit/react-ui";

import { CopilotChatInlineError } from "@/components/copilotkit/CopilotChatInlineError";

export function AgentChatSidebar(): ReactElement {
  return (
    <section
      className="flex h-full min-h-[60vh] min-w-0 flex-col overflow-hidden rounded-[24px] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.88))] shadow-[0_16px_42px_-36px_rgba(15,23,42,0.45)] xl:min-h-0"
      data-testid="agent-chat-sidebar"
    >
      <div className="border-b border-slate-200 px-4 py-3">
        <p className="text-sm font-semibold text-slate-950">Chat</p>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Follow-up questions and long tool outputs stay inside this pane.
        </p>
      </div>
      <style jsx global>{`
        .agent-chat-pane.copilotKitChat {
          display: flex;
          flex-direction: column;
          min-height: 0;
          flex: 1;
          background:
            linear-gradient(180deg, rgb(248 250 252 / 0.95) 0%, rgb(255 255 255) 18%),
            rgb(255 255 255);
        }

        .agent-chat-pane .copilotKitMessages {
          display: flex;
          min-height: 0;
          flex: 1;
          flex-direction: column;
          gap: 0;
        }

        .agent-chat-pane .copilotKitMessagesContainer {
          min-height: 0;
          flex: 1;
          gap: 0.85rem;
          overflow-y: auto;
          overscroll-behavior: contain;
          padding: 1rem 1rem 0.75rem;
        }

        .agent-chat-pane .copilotKitMessagesFooter {
          flex-shrink: 0;
          width: calc(100% - 1.5rem);
          margin-top: 0;
          padding: 0 0 0.5rem;
        }

        .agent-chat-pane .copilotKitMessage {
          max-width: min(92%, 44rem);
          margin-bottom: 0;
          border-radius: 1.1rem;
          box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
        }

        .agent-chat-pane .copilotKitMessage.copilotKitAssistantMessage {
          background: rgb(248 250 252);
          border: 1px solid rgb(226 232 240);
          border-radius: 1.1rem 1.1rem 1.1rem 0.4rem;
          overflow: hidden;
          padding: 0.8rem 0.95rem 1.25rem;
          max-width: 100%;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitUserMessage {
          border-radius: 1.1rem 1.1rem 0.4rem 1.1rem;
          padding: 0.8rem 0.95rem;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitAssistantMessage .copilotKitMessageControls {
          left: 0.95rem;
          bottom: 0.35rem;
        }

        .agent-chat-pane .copilotKitInputContainer {
          border-top: 1px solid rgb(226 232 240);
          background: rgb(255 255 255 / 0.94);
          padding: 0.85rem 0.75rem 0.55rem;
        }

        .agent-chat-pane .copilotKitInput {
          width: 100%;
          min-height: 68px;
          border-radius: 1rem;
          border-color: rgb(203 213 225);
          padding: 0.85rem 0.95rem;
          box-shadow: inset 0 1px 2px rgb(15 23 42 / 0.03);
        }

        .agent-chat-pane .copilotKitInput textarea {
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .agent-chat-pane .poweredBy {
          padding-top: 0.15rem !important;
          padding-bottom: 0 !important;
        }
      `}</style>
      <CopilotChat
        className="agent-chat-pane"
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
