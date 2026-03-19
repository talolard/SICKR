"use client";

import type { AgentMetadata } from "@/lib/agents";
import type { KnownFactItem } from "@/lib/api/threadDataClient";
import { useEffect, useState } from "react";

type MarkdownRenderer = {
  ReactMarkdown: typeof import("react-markdown").default;
  remarkGfm: typeof import("remark-gfm").default;
};

type AgentInspectorPanelProps = {
  metadata: AgentMetadata | null;
  metadataError: string;
  knownFacts: KnownFactItem[];
  knownFactsError?: string | null;
  isLoadingKnownFacts?: boolean;
};

export function AgentInspectorPanel({
  metadata,
  metadataError,
  knownFacts,
  knownFactsError = null,
  isLoadingKnownFacts = false,
}: AgentInspectorPanelProps): React.ReactElement {
  const [isDebugOpen, setIsDebugOpen] = useState<boolean>(false);
  const [isPromptOpen, setIsPromptOpen] = useState<boolean>(false);
  const [markdownRenderer, setMarkdownRenderer] = useState<MarkdownRenderer | null>(null);

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
    <aside className="flex min-h-[70vh] flex-col gap-4 rounded-[28px] border border-slate-200/80 bg-white/92 p-4 text-sm text-slate-800 shadow-[0_18px_48px_-38px_rgba(15,23,42,0.45)] backdrop-blur xl:min-h-0 xl:overflow-y-auto">
      <div className="rounded-[22px] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.86))] p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Thread context
        </p>
        <p className="mt-2 text-lg font-semibold tracking-tight text-slate-950">Known facts</p>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Durable household context collected across this thread.
        </p>
      </div>
      {knownFactsError ? <p className="text-xs text-red-700">{knownFactsError}</p> : null}
      {isLoadingKnownFacts ? <p className="text-xs text-gray-500">Loading known facts...</p> : null}
      {!isLoadingKnownFacts && !knownFactsError && knownFacts.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-3 text-xs leading-5 text-slate-600">
          Known facts will appear here after the agents store durable facts or preferences for this
          thread.
        </p>
      ) : null}
      {knownFacts.length > 0 ? (
        <ul className="space-y-3">
          {knownFacts.map((fact) => (
            <li
              className="rounded-[22px] border border-slate-200 bg-slate-50/70 px-4 py-3 shadow-[0_12px_30px_-32px_rgba(15,23,42,0.55)]"
              key={fact.memory_id}
            >
              <p className="text-sm font-medium text-slate-900">{fact.summary}</p>
            </li>
          ))}
        </ul>
      ) : null}
      {metadataError ? (
        <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">
          {metadataError}
        </p>
      ) : metadata ? (
        <details
          className="rounded-[22px] border border-slate-200 bg-white"
          data-testid="agent-inspector-debug-details"
          onToggle={(event) => {
            const nextOpen = event.currentTarget.open;
            setIsDebugOpen(nextOpen);
            if (!nextOpen) {
              setIsPromptOpen(false);
            }
          }}
        >
          <summary className="cursor-pointer list-none px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Debug details
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  Agent instructions and runtime notes
                </p>
              </div>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
                Secondary
              </span>
            </div>
          </summary>
          <div className="border-t border-slate-200 px-4 py-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                Runtime overview
              </p>
              <p className="mt-2 text-sm text-slate-700">{metadata.description}</p>
              <ul className="mt-3 flex flex-wrap gap-2 text-xs">
                {metadata.tools.map((toolName) => (
                  <li
                    className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-slate-700"
                    key={toolName}
                  >
                    {toolName}
                  </li>
                ))}
              </ul>
              {metadata.notes ? (
                <p className="mt-3 text-xs leading-5 text-slate-600">{metadata.notes}</p>
              ) : null}
            </div>
            <details
              className="mt-4 rounded-2xl border border-slate-200 bg-white"
              onToggle={(event) => setIsPromptOpen(event.currentTarget.open)}
              open={isPromptOpen}
            >
              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-slate-900">
                Prompt and instructions
              </summary>
              <div className="border-t border-slate-200 px-4 py-4">
                {isPromptOpen ? (
                  <div className="max-h-80 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-3 text-xs leading-relaxed text-slate-800">
                    {markdownRenderer ? (
                      <markdownRenderer.ReactMarkdown
                        remarkPlugins={[markdownRenderer.remarkGfm]}
                        components={{
                          h1: ({ children }) => (
                            <h3 className="mb-2 mt-3 text-sm font-semibold text-slate-900">
                              {children}
                            </h3>
                          ),
                          h2: ({ children }) => (
                            <h4 className="mb-2 mt-3 text-sm font-semibold text-slate-900">
                              {children}
                            </h4>
                          ),
                          h3: ({ children }) => (
                            <h5 className="mb-1 mt-2 font-semibold text-slate-900">{children}</h5>
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
                            <code className="rounded bg-slate-200 px-1 py-0.5 font-mono text-[11px] text-slate-900">
                              {children}
                            </code>
                          ),
                          pre: ({ children }) => (
                            <pre className="mb-2 overflow-auto rounded border border-slate-200 bg-white p-2 font-mono text-[11px] text-slate-900">
                              {children}
                            </pre>
                          ),
                          a: ({ children, href }) => (
                            <a
                              className="text-blue-700 underline"
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
                      <p className="text-xs text-slate-600">Loading markdown renderer...</p>
                    )}
                  </div>
                ) : null}
              </div>
            </details>
          </div>
        </details>
      ) : (
        <p className="rounded-2xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-xs text-slate-500">
          Loading agent metadata...
        </p>
      )}
    </aside>
  );
}
