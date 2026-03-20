import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentsPage from "./page";

vi.mock("@/components/navigation/AppNavBanner", () => ({
  AppNavBanner: ({
    agents,
    agentLoadError,
    isLoadingAgents,
  }: {
    agents: Array<{ name: string }>;
    agentLoadError: string;
    isLoadingAgents: boolean;
  }): ReactElement => (
    <div data-testid="app-nav-banner">
      <span data-testid="app-nav-loading">{String(isLoadingAgents)}</span>
      <span data-testid="app-nav-count">{agents.length}</span>
      <span data-testid="app-nav-error">{agentLoadError}</span>
    </div>
  ),
}));

vi.mock("@/components/agents/StudioShowcaseLayout", () => ({
  StudioShowcaseLayout: ({
    agents,
    error,
    isLoadingAgents,
    title,
  }: {
    agents: Array<{ name: string }>;
    error: string;
    isLoadingAgents: boolean;
    title: string;
  }): ReactElement => (
    <div data-testid="studio-showcase-layout">
      <span data-testid="layout-title">{title}</span>
      <span data-testid="layout-loading">{String(isLoadingAgents)}</span>
      <span data-testid="layout-count">{agents.length}</span>
      <span data-testid="layout-error">{error}</span>
    </div>
  ),
}));

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Agents page", () => {
  it("loads the available agents and clears the loading state", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          agents: [
            {
              name: "search",
              description: "Find products.",
              agent_key: "agent_search",
              ag_ui_path: "/ag-ui/agents/search",
            },
            {
              name: "floor_plan_intake",
              description: "Collect room layout constraints.",
              agent_key: "agent_floor_plan_intake",
              ag_ui_path: "/ag-ui/agents/floor_plan_intake",
            },
          ],
        }),
        {
          status: 200,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<AgentsPage />);

    expect(screen.getByTestId("app-nav-loading")).toHaveTextContent("true");
    expect(screen.getByTestId("layout-loading")).toHaveTextContent("true");

    await waitFor(() => {
      expect(screen.getByTestId("app-nav-loading")).toHaveTextContent("false");
      expect(screen.getByTestId("layout-loading")).toHaveTextContent("false");
    });

    expect(fetchMock).toHaveBeenCalledWith("/api/agents", { method: "GET" });
    expect(screen.getByTestId("app-nav-count")).toHaveTextContent("2");
    expect(screen.getByTestId("layout-count")).toHaveTextContent("2");
    expect(screen.getByTestId("app-nav-error")).toBeEmptyDOMElement();
    expect(screen.getByTestId("layout-error")).toBeEmptyDOMElement();
    expect(screen.getByTestId("layout-title")).toHaveTextContent(
      "Choose the studio that fits the task in front of you",
    );
  });

  it("shows the fetch error when the agent directory cannot load", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("backend unavailable", { status: 503 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByTestId("app-nav-loading")).toHaveTextContent("false");
      expect(screen.getByTestId("layout-loading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("app-nav-count")).toHaveTextContent("0");
    expect(screen.getByTestId("layout-count")).toHaveTextContent("0");
    expect(screen.getByTestId("app-nav-error")).toHaveTextContent(
      "Failed to fetch agents with status 503",
    );
    expect(screen.getByTestId("layout-error")).toHaveTextContent(
      "Failed to fetch agents with status 503",
    );
  });
});
