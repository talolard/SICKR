import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AppNavBanner } from "./AppNavBanner";

const { pushMock, usePathnameMock, useRouterMock } = vi.hoisted(() => {
  const pushMock = vi.fn<(path: string) => void>();
  const useRouterMock = vi.fn<() => { push: (path: string) => void }>(() => ({
    push: pushMock,
  }));
  const usePathnameMock = vi.fn<() => string>(() => "/");
  return { pushMock, usePathnameMock, useRouterMock };
});

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
  useRouter: useRouterMock,
}));

describe("AppNavBanner", () => {
  beforeEach(() => {
    pushMock.mockReset();
    usePathnameMock.mockReturnValue("/");
  });

  it("shows a disabled launcher while agent data is loading", () => {
    render(<AppNavBanner agents={[]} currentAgentName={null} isLoadingAgents />);

    expect(screen.getByTestId("app-nav-agent-launcher")).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Loading agent list...")).toBeInTheDocument();
  });

  it("navigates to a selected agent from the custom launcher", async () => {
    const user = userEvent.setup();

    render(
      <AppNavBanner
        agents={[
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
        ]}
        currentAgentName="search"
      />,
    );

    await user.click(screen.getByTestId("app-nav-agent-launcher-trigger"));
    await user.click(screen.getByRole("button", { name: /Floor Plan Intake/i }));

    expect(pushMock).toHaveBeenCalledWith("/agents/floor_plan_intake");
  });

  it("renders the Stitch home navigation labels and top-right chrome", () => {
    render(<AppNavBanner agents={[]} currentAgentName={null} />);

    expect(screen.getByRole("button", { name: "My Designs" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gallery" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "History" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Workspaces" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open notifications" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open settings" })).toBeInTheDocument();
  });
});
