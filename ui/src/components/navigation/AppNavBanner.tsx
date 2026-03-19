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
    : "Choose the right workspace for search, planning, or image review.";
  const launcherDisabled = isLoadingAgents || (agents.length === 0 && !agentLoadError);

  function navigateTo(nextPath: string): void {
    launcherRef.current?.removeAttribute("open");
    router.push(nextPath);
  }

  return (
    <header className="relative z-40 border-b border-slate-200/80 bg-white/75 backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1900px] flex-col gap-4 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-3">
          <button
            className="rounded-2xl border border-slate-900 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            onClick={() => navigateTo("/")}
            type="button"
          >
            IKEA Agents
          </button>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              Workspace
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight text-slate-950">
                {currentAgentLabel}
              </h1>
              {currentAgentName ? (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-900">
                  Active
                </span>
              ) : (
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                  Home
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-slate-600">{currentCapability}</p>
          </div>
        </div>

        {launcherDisabled ? (
          <div
            aria-disabled="true"
            className="min-w-[280px] rounded-[24px] border border-slate-200 bg-slate-100/80 px-4 py-3 text-left text-slate-500"
            data-testid="app-nav-agent-launcher"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              My agents
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-700">Loading agent list...</p>
            <p className="mt-1 text-xs text-slate-500">
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
              className="list-none rounded-[24px] border border-slate-200 bg-white px-4 py-3 shadow-[0_14px_40px_-36px_rgba(15,23,42,0.45)] transition hover:border-slate-300"
              data-testid="app-nav-agent-launcher-trigger"
            >
              <div className="flex cursor-pointer items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                    My agents
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-950">
                    {currentAgentName ? currentAgentLabel : "Choose a workspace"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {agents.length} workspace{agents.length === 1 ? "" : "s"} available
                  </p>
                </div>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600">
                  Open
                </span>
              </div>
            </summary>
            <div className="absolute right-0 z-30 mt-2 w-full rounded-[24px] border border-slate-200 bg-white p-2 shadow-[0_24px_60px_-36px_rgba(15,23,42,0.5)]">
              {agentLoadError ? (
                <p className="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                  {agentLoadError}
                </p>
              ) : null}
              <button
                className={`flex w-full items-center justify-between rounded-2xl px-3 py-3 text-left transition ${
                  currentAgentName === null
                    ? "bg-slate-900 text-white"
                    : "bg-slate-50 text-slate-900 hover:bg-slate-100"
                }`}
                onClick={() => navigateTo("/")}
                type="button"
              >
                <span>
                  <span className="block text-sm font-semibold">Home</span>
                  <span
                    className={`mt-1 block text-xs ${
                      currentAgentName === null ? "text-slate-200" : "text-slate-500"
                    }`}
                  >
                    Overview and agent launcher
                  </span>
                </span>
                {currentAgentName === null ? (
                  <span className="text-xs font-semibold text-slate-200">Current</span>
                ) : null}
              </button>
              <div className="mt-2 space-y-2">
                {agents.map((agent) => {
                  const active = agent.name === currentAgentName;
                  return (
                    <button
                      className={`flex w-full items-center justify-between rounded-2xl px-3 py-3 text-left transition ${
                        active
                          ? "bg-slate-900 text-white"
                          : "bg-slate-50 text-slate-900 hover:bg-slate-100"
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
                            active ? "text-slate-200" : "text-slate-500"
                          }`}
                        >
                          {describeAgentCapability(agent.name)}
                        </span>
                      </span>
                      <span
                        className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                          active
                            ? "border-white/20 bg-white/10 text-white"
                            : "border-slate-200 bg-white text-slate-600"
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
    </header>
  );
}
