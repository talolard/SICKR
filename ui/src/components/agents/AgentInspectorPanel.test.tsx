import { render, screen } from "@testing-library/react";

import { AgentInspectorPanel } from "@/components/agents/AgentInspectorPanel";
import type { AgentMetadata } from "@/lib/agents";

const metadata: AgentMetadata = {
  name: "floor_plan_intake",
  description: "Collect room constraints.",
  agent_key: "agent_floor_plan_intake",
  ag_ui_path: "/ag-ui/agents/floor_plan_intake",
  prompt_markdown: "# Prompt\n\nUse tool carefully.",
  tools: ["render_floor_plan", "confirm_floor_plan_revision"],
  notes: "Runtime note here.",
};

describe("AgentInspectorPanel", () => {
  it("renders metadata when provided", () => {
    render(<AgentInspectorPanel error="" metadata={metadata} />);

    expect(screen.getByText("Agent composition")).toBeInTheDocument();
    expect(screen.getByText("Collect room constraints.")).toBeInTheDocument();
    expect(screen.getByText("render_floor_plan")).toBeInTheDocument();
    expect(screen.getByText("Runtime note here.")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(<AgentInspectorPanel error="Failed" metadata={null} />);

    expect(screen.getByText("Failed")).toBeInTheDocument();
  });
});
