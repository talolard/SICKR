"use client";

import type { SubagentMetadata } from "@/lib/subagents";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type SubagentInspectorPanelProps = {
  metadata: SubagentMetadata | null;
  error: string;
};

export function SubagentInspectorPanel({
  metadata,
  error,
}: SubagentInspectorPanelProps): React.ReactElement {
  if (error) {
    return (
      <aside className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
        {error}
      </aside>
    );
  }

  if (!metadata) {
    return (
      <aside className="rounded border border-gray-200 bg-white p-3 text-sm text-gray-600">
        Loading subagent metadata...
      </aside>
    );
  }

  return (
    <aside className="space-y-3 rounded border border-gray-200 bg-white p-3 text-sm text-gray-800">
      <p className="text-base font-semibold text-gray-900">Subagent composition</p>
      <p>{metadata.description}</p>
      <details open>
        <summary className="cursor-pointer font-medium text-gray-900">Prompt and instructions</summary>
        <div className="mt-2 max-h-80 overflow-auto rounded border border-gray-200 bg-gray-50 p-3 text-xs leading-relaxed text-gray-800">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children }) => <h3 className="mb-2 mt-3 text-sm font-semibold text-gray-900">{children}</h3>,
              h2: ({ children }) => <h4 className="mb-2 mt-3 text-sm font-semibold text-gray-900">{children}</h4>,
              h3: ({ children }) => <h5 className="mb-1 mt-2 font-semibold text-gray-900">{children}</h5>,
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
          </ReactMarkdown>
        </div>
      </details>
      <details open>
        <summary className="cursor-pointer font-medium text-gray-900">Tools and runtime notes</summary>
        <ul className="mt-2 list-disc pl-5 text-xs">
          {metadata.tools.map((toolName) => (
            <li key={toolName}>{toolName}</li>
          ))}
        </ul>
        {metadata.notes ? <p className="mt-2 text-xs text-gray-700">{metadata.notes}</p> : null}
      </details>
    </aside>
  );
}
