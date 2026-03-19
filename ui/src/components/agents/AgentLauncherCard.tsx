"use client";

import Link from "next/link";

import type { AgentItem } from "@/lib/agents";
import { describeAgentCapability, formatAgentName } from "@/lib/agentLabels";

type AgentLauncherCardProps = {
  agent: AgentItem;
};

export function AgentLauncherCard({
  agent,
}: AgentLauncherCardProps): React.ReactElement {
  return (
    <Link
      className="group rounded-[28px] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(244,246,248,0.9))] p-5 shadow-[0_18px_48px_-38px_rgba(15,23,42,0.45)] transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_24px_60px_-36px_rgba(15,23,42,0.38)]"
      href={`/agents/${agent.name}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            {describeAgentCapability(agent.name)}
          </p>
          <p className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
            {formatAgentName(agent.name)}
          </p>
        </div>
        <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-900">
          Open
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">{agent.description}</p>
      <div className="mt-5 flex items-center justify-between border-t border-slate-200 pt-4 text-sm font-medium text-slate-700">
        <span>Launch workspace</span>
        <span className="transition group-hover:translate-x-0.5">View agent</span>
      </div>
    </Link>
  );
}
