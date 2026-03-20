"use client";

import type { AgentMetadata } from "@/lib/agents";
import type { KnownFactItem } from "@/lib/api/threadDataClient";
import { useEffect, useState } from "react";

import {
  resolveWorkspacePresentation,
  type WorkspaceRailIcon,
} from "@/components/agents/workspacePresentation";

type MarkdownRenderer = {
  ReactMarkdown: typeof import("react-markdown").default;
  remarkGfm: typeof import("remark-gfm").default;
};

type AgentInspectorPanelProps = {
  currentAgent: string;
  metadata: AgentMetadata | null;
  metadataError: string;
  knownFacts: KnownFactItem[];
  knownFactsError?: string | null;
  isLoadingKnownFacts?: boolean;
};

function RailGlyph({ icon }: { icon: WorkspaceRailIcon }): React.ReactElement {
  switch (icon) {
    case "camera":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M5.2 6.2h2.1l1-1.4h3.4l1 1.4h2.1c1 0 1.9.8 1.9 1.9v5.7c0 1-.9 1.9-1.9 1.9H5.2c-1 0-1.9-.9-1.9-1.9V8.1c0-1.1.9-1.9 1.9-1.9Z"
            stroke="currentColor"
            strokeLinejoin="round"
            strokeWidth="1.4"
          />
          <circle cx="10" cy="10.9" r="2.5" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      );
    case "favorite":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M10 15.6s-4.8-2.8-4.8-6.6a2.8 2.8 0 0 1 5-1.8 2.8 2.8 0 0 1 5 1.8c0 3.8-5.2 6.6-5.2 6.6Z"
            stroke="currentColor"
            strokeLinejoin="round"
            strokeWidth="1.4"
          />
        </svg>
      );
    case "light":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M10 3.2a4 4 0 0 0-2.8 6.9c.6.6.9 1.3 1 2h3.6c.1-.7.4-1.4 1-2A4 4 0 0 0 10 3.2Z"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.4"
          />
          <path d="M8.6 14h2.8M8.9 16h2.2" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
        </svg>
      );
    case "materials":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M5 5.5h10M5 10h10M5 14.5h10M6.5 4v12M10 4v12M13.5 4v12"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.3"
          />
        </svg>
      );
    case "payments":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M4 6.2c0-.9.7-1.7 1.7-1.7h8.6c.9 0 1.7.8 1.7 1.7v7.6c0 .9-.8 1.7-1.7 1.7H5.7c-1 0-1.7-.8-1.7-1.7z"
            stroke="currentColor"
            strokeWidth="1.4"
          />
          <path d="M4.5 8.2h11" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
          <path d="M8.2 12.4h2.5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
        </svg>
      );
    case "info":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="6.7" stroke="currentColor" strokeWidth="1.4" />
          <path d="M10 8.3v4M10 6.1h.01" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
        </svg>
      );
  }
}

export function AgentInspectorPanel({
  currentAgent,
  metadata,
  metadataError,
  knownFacts,
  knownFactsError = null,
  isLoadingKnownFacts = false,
}: AgentInspectorPanelProps): React.ReactElement {
  const [isDebugOpen, setIsDebugOpen] = useState<boolean>(false);
  const [isPromptOpen, setIsPromptOpen] = useState<boolean>(false);
  const [markdownRenderer, setMarkdownRenderer] = useState<MarkdownRenderer | null>(null);
  const presentation = resolveWorkspacePresentation(currentAgent, metadata?.description);

  useEffect(() => {
    if (!isDebugOpen || !isPromptOpen || markdownRenderer) {
      return;
    }
    let cancelled = false;
    void Promise.all([import("react-markdown"), import("remark-gfm")]).then(
      ([reactMarkdown, remarkGfmModule]) => {
        if (cancelled) {
          return;
        }
        setMarkdownRenderer({
          ReactMarkdown: reactMarkdown.default,
          remarkGfm: remarkGfmModule.default,
        });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [isDebugOpen, isPromptOpen, markdownRenderer]);

  return (
    <aside className="editorial-panel flex min-h-[70vh] flex-col gap-4 rounded-[32px] p-4 text-sm text-on-surface xl:min-h-0 xl:overflow-y-auto">
      <div className="rounded-[28px] bg-[color:var(--surface-container-lowest)] px-5 py-5 shadow-[var(--panel-shadow)]">
        <p className="editorial-eyebrow">{presentation.railEyebrow}</p>
        <h2 className="editorial-display mt-3 text-[1.9rem] leading-none text-primary">
          {presentation.railTitle}
        </h2>
        <p className="mt-4 text-sm leading-6 text-on-surface-variant">
          {presentation.railDescription}
        </p>
      </div>

      <nav className="editorial-rail-list" aria-label={`${presentation.railTitle} sections`}>
        {presentation.railItems.map((item, index) => (
          <button
            className={`editorial-rail-item ${index === 0 ? "editorial-rail-item-active" : ""}`}
            key={item.label}
            type="button"
          >
            <span className="editorial-rail-glyph">
              <RailGlyph icon={item.icon} />
            </span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <section
        className="rounded-[28px] bg-[color:var(--surface-container-lowest)] px-5 py-5 shadow-[var(--panel-shadow)]"
        data-testid="agent-known-facts-panel"
      >
        <p className="editorial-eyebrow">Known facts</p>
        <h3 className="mt-3 text-lg font-semibold tracking-tight text-primary">Current brief</h3>
        <p className="mt-2 text-sm leading-6 text-on-surface-variant">
          Durable room and project context stays here so the room brief remains visible.
        </p>
        {metadata?.description ? (
          <div className="mt-4 rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
              Agent focus
            </p>
            <p className="mt-2 text-sm leading-6 text-on-surface">{metadata.description}</p>
          </div>
        ) : null}
        {knownFactsError ? (
          <p className="mt-4 rounded-[22px] bg-red-50 px-4 py-3 text-xs text-red-700">
            {knownFactsError}
          </p>
        ) : null}
        {isLoadingKnownFacts ? (
          <p className="mt-4 text-xs text-on-surface-variant">Loading known facts...</p>
        ) : null}
        {!isLoadingKnownFacts && !knownFactsError && knownFacts.length === 0 ? (
          <p className="mt-4 rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4 text-sm leading-6 text-on-surface-variant">
            Known facts will appear here after the agent stores durable room or project facts.
          </p>
        ) : null}
        {knownFacts.length > 0 ? (
          <ul className="mt-4 space-y-3">
            {knownFacts.map((fact) => (
              <li
                className="rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4 shadow-[0_14px_30px_rgba(32,27,16,0.06)]"
                key={fact.fact_id}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                    Brief note
                  </p>
                  <span className="rounded-full bg-[color:var(--surface-container-lowest)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                    {fact.scope}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-on-surface">{fact.summary}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      {metadataError ? (
        <p className="rounded-[22px] bg-red-50 px-4 py-3 text-xs text-red-700">
          {metadataError}
        </p>
      ) : metadata ? (
        <details
          className="rounded-[28px] bg-[color:var(--surface-container-lowest)] p-1 shadow-[var(--panel-shadow)]"
          data-testid="agent-inspector-debug-details"
          onToggle={(event) => {
            const nextOpen = event.currentTarget.open;
            setIsDebugOpen(nextOpen);
            if (!nextOpen) {
              setIsPromptOpen(false);
            }
          }}
        >
          <summary className="cursor-pointer list-none rounded-[24px] px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="editorial-eyebrow">
                  Debug details
                </p>
                <p className="mt-2 text-sm font-semibold text-primary">
                  Agent instructions and runtime notes
                </p>
              </div>
              <span className="rounded-full bg-[color:var(--tertiary-fixed)] px-3 py-1 text-xs font-medium text-on-surface-variant">
                Secondary
              </span>
            </div>
          </summary>
          <div className="px-4 pb-4">
            <div className="rounded-[24px] bg-[color:var(--surface-container-low)] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                Runtime overview
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface">{metadata.description}</p>
              <ul className="mt-3 flex flex-wrap gap-2 text-xs">
                {metadata.tools.map((toolName) => (
                  <li
                    className="rounded-full bg-[color:var(--surface-container-lowest)] px-2.5 py-1 text-on-surface"
                    key={toolName}
                  >
                    {toolName}
                  </li>
                ))}
              </ul>
              {metadata.notes ? (
                <p className="mt-3 text-xs leading-5 text-on-surface-variant">{metadata.notes}</p>
              ) : null}
            </div>
            <details
              className="mt-4 rounded-[24px] bg-[color:var(--surface-container-low)] p-1"
              onToggle={(event) => setIsPromptOpen(event.currentTarget.open)}
              open={isPromptOpen}
            >
              <summary className="cursor-pointer list-none rounded-[20px] px-4 py-3 text-sm font-semibold text-primary">
                Prompt and instructions
              </summary>
              <div className="px-4 pb-4">
                {isPromptOpen ? (
                  <div className="max-h-80 overflow-auto rounded-[20px] bg-[color:var(--surface-container-lowest)] p-3 text-xs leading-relaxed text-on-surface">
                    {markdownRenderer ? (
                      <markdownRenderer.ReactMarkdown
                        remarkPlugins={[markdownRenderer.remarkGfm]}
                        components={{
                          h1: ({ children }) => (
                            <h3 className="mb-2 mt-3 text-sm font-semibold text-primary">
                              {children}
                            </h3>
                          ),
                          h2: ({ children }) => (
                            <h4 className="mb-2 mt-3 text-sm font-semibold text-primary">
                              {children}
                            </h4>
                          ),
                          h3: ({ children }) => (
                            <h5 className="mb-1 mt-2 font-semibold text-primary">{children}</h5>
                          ),
                          p: ({ children }) => (
                            <p className="mb-2 whitespace-pre-wrap">{children}</p>
                          ),
                          ul: ({ children }) => (
                            <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>
                          ),
                          code: ({ children }) => (
                            <code className="rounded bg-[color:var(--surface-container-high)] px-1 py-0.5 font-mono text-[11px] text-primary">
                              {children}
                            </code>
                          ),
                          pre: ({ children }) => (
                            <pre className="mb-2 overflow-auto rounded bg-[color:var(--surface-container-low)] p-2 font-mono text-[11px] text-primary">
                              {children}
                            </pre>
                          ),
                          a: ({ children, href }) => (
                            <a
                              className="text-primary underline"
                              href={href}
                              rel="noreferrer"
                              target="_blank"
                            >
                              {children}
                            </a>
                          ),
                        }}
                      >
                        {metadata.prompt_markdown}
                      </markdownRenderer.ReactMarkdown>
                    ) : (
                      <p className="text-xs text-on-surface-variant">Loading markdown renderer...</p>
                    )}
                  </div>
                ) : null}
              </div>
            </details>
          </div>
        </details>
      ) : (
        <p className="rounded-[22px] bg-[color:var(--surface-container-lowest)] px-4 py-3 text-xs text-on-surface-variant">
          Loading agent metadata...
        </p>
      )}
    </aside>
  );
}
