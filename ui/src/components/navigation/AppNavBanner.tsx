"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";

import type { AgentItem } from "@/lib/agents";
import { describeAgentCapability, formatAgentName } from "@/lib/agentLabels";

type AppNavBannerProps = {
  currentAgentName: string | null;
  agents: AgentItem[];
  isLoadingAgents?: boolean;
  agentLoadError?: string | null;
};

export function AppNavBanner({
  currentAgentName,
  agents,
  isLoadingAgents = false,
  agentLoadError = null,
}: AppNavBannerProps): React.ReactElement {
  const router = useRouter();
  const launcherRef = useRef<HTMLDetailsElement | null>(null);
  const currentAgentLabel = currentAgentName ? formatAgentName(currentAgentName) : "Launcher";
  const currentCapability = currentAgentName
    ? describeAgentCapability(currentAgentName)
    : "Choose the right studio for curation, planning, or image review.";
  const launcherDisabled = isLoadingAgents || (agents.length === 0 && !agentLoadError);

  function navigateTo(nextPath: string): void {
    launcherRef.current?.removeAttribute("open");
    router.push(nextPath);
  }

  return (
    <header className="editorial-glass-nav sticky top-0 z-40">
      <div className="mx-auto flex w-full max-w-[1480px] flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between lg:px-6">
        <div className="flex min-w-0 items-center gap-6">
          <button
            className="editorial-display text-2xl italic text-[color:var(--primary)] transition hover:opacity-80"
            onClick={() => navigateTo("/")}
            type="button"
          >
            The Curated Home
          </button>
          <nav className="hidden items-center gap-5 md:flex">
            <button
              className="border-b-2 border-[color:var(--primary)] pb-1 text-sm font-semibold text-[color:var(--primary)]"
              onClick={() => navigateTo("/")}
              type="button"
            >
              My Designs
            </button>
            <button
              className="pb-1 text-sm text-[color:var(--text-soft)] transition hover:text-[color:var(--primary)]"
              onClick={() => navigateTo("/agents")}
              type="button"
            >
              Workspaces
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden text-right md:block">
            <p className="editorial-eyebrow">Current Studio</p>
            <p className="mt-2 text-sm font-semibold text-[color:var(--primary)]">
              {currentAgentLabel}
            </p>
            <p className="mt-1 max-w-[18rem] text-xs text-[color:var(--text-soft)]">
              {currentCapability}
            </p>
          </div>

          {launcherDisabled ? (
            <div
              aria-disabled="true"
              className="min-w-[280px] rounded-[24px] bg-[color:var(--surface-lowest)] px-4 py-3 text-left text-[color:var(--text-soft)] shadow-[0_16px_30px_rgba(32,27,16,0.08)]"
              data-testid="app-nav-agent-launcher"
            >
              <p className="editorial-eyebrow">Studio Menu</p>
              <p className="mt-2 text-sm font-semibold text-[color:var(--primary)]">
                Loading agent list...
              </p>
              <p className="mt-1 text-xs text-[color:var(--text-soft)]">
                The launcher becomes interactive once the workspaces are ready.
              </p>
            </div>
          ) : (
            <details
              className="relative min-w-[280px]"
              data-testid="app-nav-agent-launcher"
              ref={launcherRef}
            >
              <summary
                className="cursor-pointer rounded-[24px] bg-[color:var(--surface-lowest)] px-4 py-3 shadow-[0_16px_30px_rgba(32,27,16,0.08)]"
                data-testid="app-nav-agent-launcher-trigger"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="editorial-eyebrow">Studio Menu</p>
                    <p className="mt-2 text-sm font-semibold text-[color:var(--primary)]">
                      {currentAgentName ? currentAgentLabel : "Choose a workspace"}
                    </p>
                    <p className="mt-1 text-xs text-[color:var(--text-soft)]">
                      {agents.length} workspace{agents.length === 1 ? "" : "s"} available
                    </p>
                  </div>
                  <span className="editorial-chip px-3 py-1 text-xs font-semibold">
                    Open
                  </span>
                </div>
              </summary>
              <div className="editorial-card absolute right-0 z-30 mt-3 w-full rounded-[28px] p-3">
                {agentLoadError ? (
                  <p className="rounded-[20px] bg-red-50 px-3 py-2 text-xs text-red-700">
                    {agentLoadError}
                  </p>
                ) : null}
                <button
                  className={`flex w-full items-center justify-between rounded-[22px] px-4 py-3 text-left transition ${
                    currentAgentName === null
                      ? "editorial-button-primary"
                      : "bg-[color:var(--surface-low)] text-[color:var(--primary)] hover:bg-[color:var(--surface-high)]"
                  }`}
                  onClick={() => navigateTo("/")}
                  type="button"
                >
                  <span>
                    <span className="block text-sm font-semibold">Home</span>
                    <span
                      className={`mt-1 block text-xs ${
                        currentAgentName === null ? "text-white/75" : "text-[color:var(--text-soft)]"
                      }`}
                    >
                      Studio overview and workspace launcher
                    </span>
                  </span>
                  {currentAgentName === null ? (
                    <span className="text-xs font-semibold text-white/80">Current</span>
                  ) : null}
                </button>
                <div className="mt-2 space-y-2">
                  {agents.map((agent) => {
                    const active = agent.name === currentAgentName;
                    return (
                      <button
                        className={`flex w-full items-center justify-between rounded-[22px] px-4 py-3 text-left transition ${
                          active
                            ? "editorial-button-primary"
                            : "bg-[color:var(--surface-low)] text-[color:var(--primary)] hover:bg-[color:var(--surface-high)]"
                        }`}
                        key={agent.name}
                        onClick={() => navigateTo(`/agents/${agent.name}`)}
                        type="button"
                      >
                        <span>
                          <span className="block text-sm font-semibold">
                            {formatAgentName(agent.name)}
                          </span>
                          <span
                            className={`mt-1 block text-xs ${
                              active ? "text-white/75" : "text-[color:var(--text-soft)]"
                            }`}
                          >
                            {describeAgentCapability(agent.name)}
                          </span>
                        </span>
                        <span
                          className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                            active
                              ? "bg-white/14 text-white"
                              : "bg-[color:var(--tertiary-fixed)] text-[color:var(--text-primary)]"
                          }`}
                        >
                          {active ? "Current" : "Open"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </details>
          )}
        </div>
      </div>
    </header>
  );
}
