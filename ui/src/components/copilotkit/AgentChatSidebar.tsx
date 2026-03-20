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
      className="editorial-panel flex h-full min-h-[60vh] min-w-0 flex-col overflow-hidden rounded-[32px] p-2.5 xl:min-h-0"
      data-testid="agent-chat-sidebar"
    >
      <div className="rounded-[24px] bg-[color:var(--surface-container-lowest)] px-4 py-4 shadow-[var(--panel-shadow)]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[color:var(--primary)] text-white shadow-[0_20px_35px_rgba(24,36,27,0.18)]">
              <SparkGlyph />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                {presentation.consultationEyebrow}
              </p>
              <h2 className="mt-1 text-lg font-semibold tracking-tight text-primary">
                {presentation.consultationTitle}
              </h2>
            </div>
          </div>
          <div className="inline-flex items-center rounded-full bg-[color:var(--tertiary-fixed)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
            {presentation.consultationModeLabel}
          </div>
        </div>
        <p className="mt-3 text-xs leading-5 text-on-surface-variant">
          {presentation.consultationDescription}
        </p>
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
          margin-top: 0.45rem;
          border-radius: 1.55rem;
          background: color-mix(in srgb, var(--surface-container-lowest) 94%, transparent);
          box-shadow: var(--panel-shadow);
          padding: 0.35rem 0 0.2rem;
        }

        .agent-chat-pane .copilotKitMessagesContainer {
          display: flex;
          flex-direction: column;
          min-height: 0;
          flex: 1;
          gap: 0.85rem;
          overflow-y: auto;
          overscroll-behavior: contain;
          padding: 0.75rem 0.65rem 0.65rem;
        }

        .agent-chat-pane .copilotKitMessagesContainer > * {
          flex-shrink: 0;
        }

        .agent-chat-pane .copilotKitMessagesFooter {
          flex-shrink: 0;
          width: calc(100% - 0.9rem);
          margin-top: 0.25rem;
          padding: 0 0 0.35rem;
        }

        .agent-chat-pane .copilotKitMessage {
          max-width: min(92%, 28rem);
          margin-bottom: 0;
          border-radius: 1.25rem;
          box-shadow: var(--panel-shadow);
          min-width: 0;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitAssistantMessage {
          background: var(--surface-container-lowest);
          border: 0;
          border-radius: 1.25rem 1.25rem 1.25rem 0.55rem;
          overflow: hidden;
          padding: 0.9rem;
          max-width: 100%;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitUserMessage {
          background: linear-gradient(135deg, var(--primary) 0%, var(--primary-container) 100%);
          color: white;
          margin-left: auto;
          border-radius: 1.25rem 1.25rem 0.55rem 1.25rem;
          padding: 0.9rem;
        }

        .agent-chat-pane .copilotKitMessage.copilotKitAssistantMessage .copilotKitMessageControls {
          position: static;
          left: auto;
          right: auto;
          bottom: auto;
          margin-top: 0.7rem;
          justify-content: flex-end;
          gap: 0.3rem;
          border-top: 1px solid color-mix(in srgb, var(--outline-variant) 55%, transparent);
          padding-top: 0.5rem;
        }

        .agent-chat-pane .copilotKitInputContainer {
          background: color-mix(in srgb, var(--surface-container-low) 90%, transparent);
          border-top: 0;
          margin-top: 0.2rem;
          padding: 0.65rem 0.45rem 0.3rem;
        }

        .agent-chat-pane .copilotKitInput {
          width: 100%;
          min-height: 64px;
          border-radius: 1.2rem;
          background: var(--surface-container-lowest);
          border: 0;
          padding: 0.85rem 0.95rem;
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

        .agent-chat-pane .copilotKitMarkdown,
        .agent-chat-pane .copilotKitMarkdownElement,
        .agent-chat-pane .copilotKitMessage p,
        .agent-chat-pane .copilotKitMessage li,
        .agent-chat-pane .copilotKitMessage span {
          overflow-wrap: anywhere;
          word-break: break-word;
        }

        .agent-chat-pane .copilotKitMessage pre,
        .agent-chat-pane .copilotKitMessage code {
          white-space: pre-wrap;
          overflow-wrap: anywhere;
          word-break: break-word;
        }

        .agent-chat-pane .copilotKitInputControls {
          color: var(--primary);
        }

        .agent-chat-pane .poweredBy {
          color: color-mix(in srgb, var(--on-surface-variant) 58%, transparent) !important;
          padding-top: 0.25rem !important;
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
