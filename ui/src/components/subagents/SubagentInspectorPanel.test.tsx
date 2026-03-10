import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SubagentInspectorPanel } from "@/components/subagents/SubagentInspectorPanel";
import type { SubagentMetadata } from "@/lib/subagents";

const metadata: SubagentMetadata = {
  name: "floor_plan_intake",
  description: "Collect initial room architecture and render iterative floor-plan drafts.",
  agent_key: "subagent_floor_plan_intake",
  ag_ui_path: "/ag-ui/subagents/floor_plan_intake",
  prompt_markdown: [
    "# Floor Plan Intake Subagent Prompt",
    "",
    "Use this checklist:",
    "",
    "- Keep this low-stakes and iterative.",
    "- Ask follow-up questions.",
    "",
    "Read the [graph notes](https://example.com/graph).",
  ].join("\n"),
  tools: ["render_floor_plan", "confirm_floor_plan_revision"],
  notes: "Runtime notes",
};

describe("SubagentInspectorPanel", () => {
  it("renders prompt markdown as structured content", () => {
    render(<SubagentInspectorPanel error="" metadata={metadata} />);

    expect(
      screen.getByRole("heading", { name: "Floor Plan Intake Subagent Prompt" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Keep this low-stakes and iterative.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "graph notes" })).toHaveAttribute(
      "href",
      "https://example.com/graph",
    );
  });
});
