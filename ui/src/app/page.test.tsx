import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import Home from "./page";
import type { AgentItem } from "@/lib/agents";

const { fetchAgentsMock } = vi.hoisted(() => ({
  fetchAgentsMock: vi.fn<() => Promise<AgentItem[]>>(async () => []),
}));

vi.mock("@/lib/agents", () => ({
  fetchAgents: fetchAgentsMock,
}));

vi.mock("@/components/navigation/AppNavBanner", () => ({
  AppNavBanner: (): ReactElement => <div data-testid="app-nav-banner" />,
}));

describe("Home page", () => {
  it("renders available agents as links", async () => {
    fetchAgentsMock.mockResolvedValueOnce([
      {
        name: "floor_plan_intake",
        description: "Collect room layout constraints.",
        agent_key: "agent_floor_plan_intake",
        ag_ui_path: "/ag-ui/agents/floor_plan_intake",
      },
      {
        name: "search",
        description: "Find products.",
        agent_key: "agent_search",
        ag_ui_path: "/ag-ui/agents/search",
      },
    ]);

    render(<Home />);

    expect(await screen.findByRole("link", { name: /floor plan intake/i })).toHaveAttribute(
      "href",
      "/agents/floor_plan_intake",
    );
    expect(await screen.findByRole("link", { name: /search/i })).toHaveAttribute(
      "href",
      "/agents/search",
    );
    expect(screen.getByTestId("app-nav-banner")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /View All Archives/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Room Facts/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Chat/i })).toBeInTheDocument();
    expect(screen.getByText("Design Consultation")).toBeInTheDocument();
  });
});
