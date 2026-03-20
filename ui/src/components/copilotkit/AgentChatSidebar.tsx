"use client";

import type { ReactElement } from "react";
import { CopilotChat } from "@copilotkit/react-ui";

import { resolveWorkspacePresentation } from "@/components/agents/workspacePresentation";
import { CopilotChatInlineError } from "@/components/copilotkit/CopilotChatInlineError";

type AgentChatSidebarProps = {
  currentAgent: string;
};

function SparkGlyph(): ReactElement {
  return (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
      <path
        d="M10 3.2l1.4 3.5 3.4 1.3-3.4 1.3-1.4 3.5-1.4-3.5-3.4-1.3 3.4-1.3z"
        fill="currentColor"
      />
    </svg>
  );
}

export function AgentChatSidebar({ currentAgent }: AgentChatSidebarProps): ReactElement {
  const presentation = resolveWorkspacePresentation(currentAgent);

  return (
    <section
      className="editorial-panel flex h-full min-h-[60vh] min-w-0 flex-col overflow-hidden rounded-[32px] p-3 xl:min-h-0"
      data-testid="agent-chat-sidebar"
    >
      <div className="rounded-[26px] bg-[color:var(--surface-container-lowest)] px-5 py-5 shadow-[var(--panel-shadow)]">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[color:var(--primary)] text-white shadow-[0_20px_35px_rgba(24,36,27,0.18)]">
            <SparkGlyph />
          </div>
          <div>
            <p className="editorial-eyebrow">{presentation.consultationEyebrow}</p>
            <h2 className="editorial-display mt-2 text-[1.55rem] leading-none text-primary">
              {presentation.consultationTitle}
            </h2>
          </div>
        </div>
        <p className="mt-4 text-sm leading-6 text-on-surface-variant">
          {presentation.consultationDescription}
        </p>
        <div className="mt-4 inline-flex items-center rounded-full bg-[color:var(--tertiary-fixed)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
          {presentation.consultationModeLabel}
        </div>
      </div>
      <style jsx global>{`
        .agent-chat-pane.copilotKitChat {
          display: flex;
          flex-direction: column;
          min-height: 0;
          flex: 1;
          background: transparent;
          overflow: hidden;
        }

        .agent-chat-pane .copilotKitMessages {
          display: flex;
          min-height: 0;
          flex: 1;
          flex-direction: column;
          gap: 0;
          overflow: hidden;
        }

        .agent-chat-pane .copilotKitMessagesContainer {
          display: flex;
          flex-direction: column;
          min-height: 0;
          flex: 1;
          gap: 1rem;
          overflow-y: auto;
          overscroll-behavior: contain;
          padding: 1rem 0.55rem 0.55rem;
        }

        .agent-chat-pane .copilotKitMessagesContainer > * {
          flex-shrink: 0;
        }

        .agent-chat-pane .copilotKitMessagesFooter {
          flex-shrink: 0;
          width: calc(100% - 1rem);
          margin-top: 0;
          padding: 0 0 0.4rem;
        }

        .agent-chat-pane .copilotKitMessage {
          max-width: min(92%, 28rem);
          margin-bottom: 0;
          border-radius: 1.5rem;
          box-shadow: var(--panel-shadow);
        }

        .agent-chat-pane .copilotKitMessage.copilotKitAssistantMessage {
          background: var(--surface-container-lowest);
          border: 0;
          border-radius: 1.5rem 1.5rem 1.5rem 0.6rem;
          overflow: hidden;
          padding: 1rem;
          max-width: 100%;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitUserMessage {
          background: linear-gradient(135deg, var(--primary) 0%, var(--primary-container) 100%);
          color: white;
          margin-left: auto;
          border-radius: 1.5rem 1.5rem 0.6rem 1.5rem;
          padding: 1rem;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitAssistantMessage .copilotKitMessageControls {
          position: static;
          left: auto;
          right: auto;
          bottom: auto;
          margin-top: 0.85rem;
          justify-content: flex-end;
          gap: 0.3rem;
          border-top: 1px solid color-mix(in srgb, var(--outline-variant) 55%, transparent);
          padding-top: 0.55rem;
        }

        .agent-chat-pane .copilotKitInputContainer {
          background: color-mix(in srgb, var(--surface-container-low) 90%, transparent);
          border-top: 0;
          margin-top: 0.25rem;
          padding: 0.75rem 0.5rem 0.35rem;
        }

        .agent-chat-pane .copilotKitInput {
          width: 100%;
          min-height: 72px;
          border-radius: 1.35rem;
          background: var(--surface-container-lowest);
          border: 0;
          padding: 0.95rem 1rem;
          box-shadow: 0 0 0 1px rgb(24 36 27 / 0.08), var(--panel-shadow);
        }

        .agent-chat-pane .copilotKitInput textarea {
          color: var(--on-surface);
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .agent-chat-pane .copilotKitInput textarea::placeholder {
          color: color-mix(in srgb, var(--on-surface-variant) 82%, transparent);
        }

        .agent-chat-pane .copilotKitInputControls {
          color: var(--primary);
        }

        .agent-chat-pane .poweredBy {
          color: color-mix(in srgb, var(--on-surface-variant) 58%, transparent) !important;
          padding-top: 0.3rem !important;
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
