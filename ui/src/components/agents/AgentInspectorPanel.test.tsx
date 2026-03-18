import { render, screen } from "@testing-library/react";

import { AgentInspectorPanel } from "@/components/agents/AgentInspectorPanel";
import type { KnownFactItem } from "@/lib/api/threadDataClient";
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

const knownFacts: KnownFactItem[] = [
  {
    memory_id: "rmem-1",
    kind: "constraint",
    summary: "User has toddlers, keep things elevated.",
    source_message_text: "We have a toddler at home.",
    updated_at: "2026-03-18T12:00:00Z",
    run_id: "run-1",
  },
];

describe("AgentInspectorPanel", () => {
  it("renders known facts and metadata details when provided", () => {
    render(
      <AgentInspectorPanel
        error=""
        isLoadingKnownFacts={false}
        knownFacts={knownFacts}
        metadata={metadata}
      />,
    );

    expect(screen.getByText("Known facts")).toBeInTheDocument();
    expect(screen.getByText("User has toddlers, keep things elevated.")).toBeInTheDocument();
    expect(screen.getByText("render_floor_plan")).toBeInTheDocument();
    expect(screen.getByText("Runtime note here.")).toBeInTheDocument();
  });

  it("renders an empty known-facts state", () => {
    render(
      <AgentInspectorPanel
        error=""
        isLoadingKnownFacts={false}
        knownFacts={[]}
        metadata={metadata}
      />,
    );

    expect(screen.getByText(/Known facts will appear here/i)).toBeInTheDocument();
  });

  it("keeps known facts visible while metadata is still loading", () => {
    render(
      <AgentInspectorPanel
        error=""
        isLoadingKnownFacts={false}
        knownFacts={knownFacts}
        metadata={null}
      />,
    );

    expect(screen.getByText("User has toddlers, keep things elevated.")).toBeInTheDocument();
    expect(screen.getByText("Loading agent metadata...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(
      <AgentInspectorPanel
        error="Failed"
        isLoadingKnownFacts={false}
        knownFacts={[]}
        metadata={null}
      />,
    );

    expect(screen.getByText("Failed")).toBeInTheDocument();
  });
});
