import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MermaidDiagram, normalizeMermaidSource } from "@/components/subagents/MermaidDiagram";

const initializeMock = vi.fn();
const renderMock = vi.fn<
  (id: string, text: string) => Promise<{ svg: string }>
>();

vi.mock("mermaid", () => ({
  default: {
    initialize: initializeMock,
    render: renderMock,
  },
}));

describe("normalizeMermaidSource", () => {
  it("strips YAML front matter from graph source", () => {
    const source = ["---", "title: floor_plan_intake", "---", "stateDiagram-v2", "A --> B"].join(
      "\n",
    );
    expect(normalizeMermaidSource(source)).toBe("stateDiagram-v2\nA --> B");
  });
});

describe("MermaidDiagram", () => {
  beforeEach(() => {
    initializeMock.mockReset();
    renderMock.mockReset();
    renderMock.mockResolvedValue({ svg: "<svg><text>ok</text></svg>" });
  });

  it("renders an SVG diagram", async () => {
    render(<MermaidDiagram source={"stateDiagram-v2\nA --> B"} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Mermaid diagram")).toBeInTheDocument();
    });
    expect(initializeMock).toHaveBeenCalledTimes(1);
    expect(renderMock).toHaveBeenCalledTimes(1);
    const renderArgs = renderMock.mock.calls[0];
    expect(renderArgs?.[1]).toBe("stateDiagram-v2\nA --> B");
  });

  it("falls back to source text on render failure", async () => {
    renderMock.mockRejectedValueOnce(new Error("invalid graph"));

    render(<MermaidDiagram source={"stateDiagram-v2\nbroken"} />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to render Mermaid diagram/i)).toBeInTheDocument();
    });
    const sourceFallback = screen.getByText(/stateDiagram-v2/);
    expect(sourceFallback.tagName).toBe("PRE");
    expect(sourceFallback).toHaveTextContent(/stateDiagram-v2\s+broken/);
  });
});
