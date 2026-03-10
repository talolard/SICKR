"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type MermaidDiagramProps = {
  source: string;
};

type MermaidRenderResult = {
  svg: string;
};

type MermaidApi = {
  initialize: (config: {
    startOnLoad: boolean;
    securityLevel: "strict" | "loose" | "antiscript" | "sandbox";
    theme: "default" | "neutral" | "dark" | "forest";
  }) => void;
  render: (id: string, text: string) => Promise<MermaidRenderResult>;
};

let mermaidInitialized = false;

function normalizeMermaidSource(source: string): string {
  const trimmed = source.trim();
  if (!trimmed.startsWith("---")) {
    return trimmed;
  }
  const lines = trimmed.split("\n");
  const closingFrontMatterIndex = lines.findIndex(
    (line, index) => index > 0 && line.trim() === "---",
  );
  if (closingFrontMatterIndex === -1) {
    return trimmed;
  }
  return lines.slice(closingFrontMatterIndex + 1).join("\n").trim();
}

function ensureMermaidInitialized(mermaid: MermaidApi): void {
  if (mermaidInitialized) {
    return;
  }
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "neutral",
  });
  mermaidInitialized = true;
}

export function MermaidDiagram({ source }: MermaidDiagramProps): React.ReactElement {
  const normalizedSource = useMemo(() => normalizeMermaidSource(source), [source]);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string>("");
  const renderIdRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const renderDiagram = async (): Promise<void> => {
      try {
        setError("");
        setSvg("");
        if (!normalizedSource) {
          setError("Mermaid source is empty.");
          return;
        }
        const mermaidModule = await import("mermaid");
        const mermaid = mermaidModule.default as unknown as MermaidApi;
        ensureMermaidInitialized(mermaid);
        renderIdRef.current += 1;
        const renderId = `subagent-mermaid-${renderIdRef.current}`;
        const rendered = await mermaid.render(renderId, normalizedSource);
        if (cancelled) {
          return;
        }
        setSvg(rendered.svg);
      } catch {
        if (cancelled) {
          return;
        }
        setError("Unable to render Mermaid diagram. Showing source instead.");
      }
    };

    void renderDiagram();
    return () => {
      cancelled = true;
    };
  }, [normalizedSource]);

  if (error) {
    return (
      <div className="mt-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
        <p>{error}</p>
        <pre className="mt-2 max-h-80 overflow-auto rounded border border-amber-200 bg-white p-2 text-[11px]">
          {source}
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="mt-2 rounded border border-gray-200 bg-gray-50 p-2 text-xs text-gray-600">
        Rendering Mermaid diagram...
      </div>
    );
  }

  return (
    <div
      aria-label="Mermaid diagram"
      className="mt-2 overflow-auto rounded border border-gray-200 bg-white p-2"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

export { normalizeMermaidSource };
