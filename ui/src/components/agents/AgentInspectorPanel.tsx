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
  error: string;
  knownFacts: KnownFactItem[];
  knownFactsError?: string | null;
  isLoadingKnownFacts?: boolean;
};

export function AgentInspectorPanel({
  metadata,
  error,
  knownFacts,
  knownFactsError = null,
  isLoadingKnownFacts = false,
}: AgentInspectorPanelProps): React.ReactElement {
  const [isPromptOpen, setIsPromptOpen] = useState<boolean>(false);
  const [markdownRenderer, setMarkdownRenderer] = useState<MarkdownRenderer | null>(null);

  useEffect(() => {
    if (!isPromptOpen || markdownRenderer) {
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
  }, [isPromptOpen, markdownRenderer]);

  return (
    <aside className="space-y-3 rounded border border-gray-200 bg-white p-3 text-sm text-gray-800">
      <div>
        <p className="text-base font-semibold text-gray-900">Known facts</p>
        <p className="mt-1 text-xs text-gray-600">
          Durable household context collected across this thread.
        </p>
      </div>
      {knownFactsError ? <p className="text-xs text-red-700">{knownFactsError}</p> : null}
      {isLoadingKnownFacts ? <p className="text-xs text-gray-500">Loading known facts...</p> : null}
      {!isLoadingKnownFacts && !knownFactsError && knownFacts.length === 0 ? (
        <p className="rounded border border-dashed border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
          Known facts will appear here after the agents store durable facts or preferences for this
          thread.
        </p>
      ) : null}
      {knownFacts.length > 0 ? (
        <ul className="space-y-2">
          {knownFacts.map((fact) => (
            <li className="rounded border border-gray-200 bg-gray-50 px-3 py-2" key={fact.memory_id}>
              <p className="text-sm text-gray-900">{fact.summary}</p>
            </li>
          ))}
        </ul>
      ) : null}
      {error ? (
        <p className="text-xs text-red-700">{error}</p>
      ) : metadata ? (
        <>
          <details
            onToggle={(event) => setIsPromptOpen(event.currentTarget.open)}
            open={isPromptOpen}
          >
            <summary className="cursor-pointer font-medium text-gray-900">Prompt and instructions</summary>
            {isPromptOpen ? (
              <div className="mt-2 max-h-80 overflow-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs leading-relaxed text-gray-800">
                {markdownRenderer ? (
                  <markdownRenderer.ReactMarkdown
                    remarkPlugins={[markdownRenderer.remarkGfm]}
                    components={{
                      h1: ({ children }) => (
                        <h3 className="mb-2 mt-3 text-sm font-semibold text-gray-900">{children}</h3>
                      ),
                      h2: ({ children }) => (
                        <h4 className="mb-2 mt-3 text-sm font-semibold text-gray-900">{children}</h4>
                      ),
                      h3: ({ children }) => (
                        <h5 className="mb-1 mt-2 font-semibold text-gray-900">{children}</h5>
                      ),
                      p: ({ children }) => <p className="mb-2 whitespace-pre-wrap">{children}</p>,
                      ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>,
                      ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>,
                      code: ({ children }) => (
                        <code className="rounded bg-gray-200 px-1 py-0.5 font-mono text-[11px] text-gray-900">
                          {children}
                        </code>
                      ),
                      pre: ({ children }) => (
                        <pre className="mb-2 overflow-auto rounded border border-gray-200 bg-white p-2 font-mono text-[11px] text-gray-900">
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
                  <p className="text-xs text-gray-600">Loading markdown renderer...</p>
                )}
              </div>
            ) : null}
          </details>
          <details open>
            <summary className="cursor-pointer font-medium text-gray-900">Tools and runtime notes</summary>
            <p className="mt-2 text-xs text-gray-700">{metadata.description}</p>
            <ul className="mt-2 list-disc pl-5 text-xs">
              {metadata.tools.map((toolName) => (
                <li key={toolName}>{toolName}</li>
              ))}
            </ul>
            {metadata.notes ? <p className="mt-2 text-xs text-gray-700">{metadata.notes}</p> : null}
          </details>
        </>
      ) : (
        <p className="text-xs text-gray-500">Loading agent metadata...</p>
      )}
    </aside>
  );
}
