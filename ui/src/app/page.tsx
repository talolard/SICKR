"use client";

import { useEffect, useState } from "react";

import { AgentLauncherCard } from "@/components/agents/AgentLauncherCard";
import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { fetchAgents, type AgentItem } from "@/lib/agents";

export default function Home(): React.ReactElement {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [error, setError] = useState<string>("");
  const [isLoadingAgents, setIsLoadingAgents] = useState<boolean>(true);

  useEffect(() => {
    void fetchAgents()
      .then((items) => {
        setAgents(items);
        setError("");
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agents.";
        setError(message);
      })
      .finally(() => {
        setIsLoadingAgents(false);
      });
  }, []);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(246,219,138,0.16),transparent_28%),radial-gradient(circle_at_top_right,rgba(31,74,123,0.12),transparent_30%),linear-gradient(180deg,#f6f3ee_0%,#f2eee8_46%,#ece7df_100%)]">
      <AppNavBanner
        currentAgentName={null}
        agents={agents}
        agentLoadError={error}
        isLoadingAgents={isLoadingAgents}
      />
      <section className="mx-auto max-w-[1720px] px-4 py-4 pb-6">
        <section className="rounded-[32px] border border-slate-200/80 bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(247,244,239,0.92))] p-6 shadow-[0_22px_60px_-42px_rgba(15,23,42,0.5)]">
          <div className="max-w-3xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              IKEA agent workspace
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">
              Pick the agent that matches the task in front of you.
            </h2>
            <p className="mt-3 text-base leading-7 text-slate-600">
              Each workspace pairs chat with structured outputs so you can move from room context
              to product results, bundles, and floor-plan decisions without losing the thread.
            </p>
          </div>
        </section>

        {error ? (
          <p className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
          {isLoadingAgents
            ? Array.from({ length: 3 }, (_, index) => (
                <div
                  className="rounded-[28px] border border-slate-200 bg-white/70 p-5 text-sm text-slate-500"
                  key={`agent-loading-${index}`}
                >
                  Loading agent...
                </div>
              ))
            : agents.map((agent) => <AgentLauncherCard agent={agent} key={agent.name} />)}
        </div>
      </section>
    </main>
  );
}
