import { render, screen } from "@testing-library/react";

import { StudioShowcaseLayout } from "./StudioShowcaseLayout";
import type { AgentItem } from "@/lib/agents";

const agentsOutOfOrder: AgentItem[] = [
  {
    name: "floor_plan_intake",
    description: "Collect room layout constraints.",
    agent_key: "agent_floor_plan_intake",
    ag_ui_path: "/ag-ui/agents/floor_plan_intake",
  },
  {
    name: "image_analysis",
    description: "Analyze room photos.",
    agent_key: "agent_image_analysis",
    ag_ui_path: "/ag-ui/agents/image_analysis",
  },
  {
    name: "search",
    description: "Find products.",
    agent_key: "agent_search",
    ag_ui_path: "/ag-ui/agents/search",
  },
];

describe("StudioShowcaseLayout", () => {
  function renderLayout(): void {
    render(
      <StudioShowcaseLayout
        agents={agentsOutOfOrder}
        description="Curated home design help."
        error=""
        eyebrow="Designer's Studio"
        isLoadingAgents={false}
        title="Welcome to your Designer's Studio"
      />,
    );
  }

  it("renders cards in the intended editorial order", () => {
    renderLayout();

    expect(screen.getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
      "/agents/search",
      "/agents/floor_plan_intake",
      "/agents/image_analysis",
    ]);
  });

  it("renders the simplified consultation rail without a new badge", () => {
    renderLayout();

    expect(screen.getByRole("button", { name: "Chat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Suggestions" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "History" })).toBeInTheDocument();
    expect(screen.queryByText("NEW")).not.toBeInTheDocument();
  });

  it("keeps the home shell split into dedicated left, center, and right regions", () => {
    renderLayout();

    expect(screen.getByTestId("studio-showcase-left-rail")).toBeInTheDocument();
    expect(screen.getByTestId("studio-showcase-main")).toBeInTheDocument();
    expect(screen.getByTestId("studio-showcase-right-rail")).toBeInTheDocument();
    expect(
      screen.getByText(/I've noticed your preference for Belgian linen/i),
    ).toBeInTheDocument();
  });
});
