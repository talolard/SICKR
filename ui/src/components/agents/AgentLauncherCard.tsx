"use client";

import Link from "next/link";

import type { AgentItem } from "@/lib/agents";
import { formatAgentName } from "@/lib/agentLabels";

type AgentLauncherCardProps = {
  agent: AgentItem;
};

type AgentStudioCardContent = {
  eyebrow: string;
  headline: string;
  cta: string;
  accent: "forest" | "terracotta" | "stone";
};

function getAgentStudioCardContent(agentName: string): AgentStudioCardContent {
  switch (agentName) {
    case "search":
      return {
        eyebrow: "Product discovery",
        headline: "Find the right pieces for your space",
        cta: "Start Designing",
        accent: "forest",
      };
    case "floor_plan_intake":
      return {
        eyebrow: "Room planning",
        headline: "Plan your room with confidence",
        cta: "Begin Planning",
        accent: "terracotta",
      };
    case "image_analysis":
      return {
        eyebrow: "Image review",
        headline: "Get design guidance from your space",
        cta: "Get Guidance",
        accent: "stone",
      };
    default:
      return {
        eyebrow: "Specialized workflow",
        headline: `Open ${formatAgentName(agentName)}`,
        cta: "Open Workspace",
        accent: "forest",
      };
  }
}

function AgentPreviewArt({ accent }: { accent: AgentStudioCardContent["accent"] }): React.ReactElement {
  if (accent === "terracotta") {
    return (
      <div className="relative h-44 overflow-hidden rounded-[28px] bg-[linear-gradient(180deg,#f8efe5,#f4e4d3)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(130,84,41,0.06),transparent_58%)]" />
        <div className="absolute inset-8 rounded-[24px] border border-[rgba(130,84,41,0.18)]" />
        <div className="absolute inset-x-14 top-16 h-px bg-[rgba(130,84,41,0.18)]" />
        <div className="absolute inset-y-12 left-1/2 w-px -translate-x-1/2 bg-[rgba(130,84,41,0.14)]" />
        <div className="absolute bottom-12 left-14 h-16 w-16 rounded-tr-full border-r border-t border-[rgba(130,84,41,0.22)]" />
      </div>
    );
  }

  if (accent === "stone") {
    return (
      <div className="relative h-44 overflow-hidden rounded-[28px] bg-[linear-gradient(180deg,#f7f2ea,#ece2d5)]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(45,57,48,0.08),transparent_26%),radial-gradient(circle_at_bottom_right,rgba(130,84,41,0.12),transparent_28%)]" />
        <div className="absolute left-8 top-9 h-20 w-16 rounded-[20px] bg-white/55" />
        <div className="absolute bottom-10 left-[6.5rem] h-24 w-24 rounded-[26px] bg-white/70 shadow-[0_16px_30px_rgba(32,27,16,0.08)]" />
        <div className="absolute right-8 top-8 h-28 w-20 rounded-[22px] bg-[rgba(255,255,255,0.52)]" />
      </div>
    );
  }

  return (
    <div className="relative h-44 overflow-hidden rounded-[28px] bg-[linear-gradient(180deg,#f6efe4,#efe4d3)]">
      <div className="absolute inset-x-10 bottom-8 h-11 rounded-[22px] bg-[rgba(45,57,48,0.16)]" />
      <div className="absolute inset-x-14 bottom-16 h-9 rounded-[18px] bg-[rgba(45,57,48,0.22)]" />
      <div className="absolute left-9 top-9 h-20 w-20 rounded-full bg-[rgba(130,84,41,0.12)] blur-[1px]" />
      <div className="absolute right-10 top-10 h-24 w-10 rounded-full bg-[rgba(24,36,27,0.12)]" />
    </div>
  );
}

export function AgentLauncherCard({
  agent,
}: AgentLauncherCardProps): React.ReactElement {
  const content = getAgentStudioCardContent(agent.name);
  const agentLabel = formatAgentName(agent.name);

  return (
    <Link
      className="group editorial-card flex h-full flex-col overflow-hidden rounded-[32px] p-4 transition hover:-translate-y-1 hover:shadow-[0_50px_90px_rgba(32,27,16,0.12)]"
      href={`/agents/${agent.name}`}
    >
      <AgentPreviewArt accent={content.accent} />
      <div className="flex flex-1 flex-col px-4 pb-4 pt-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="editorial-eyebrow">{content.eyebrow}</p>
            <h3 className="editorial-display mt-4 text-4xl leading-[0.94] text-[color:var(--primary)]">
              {content.headline}
            </h3>
          </div>
          <span className="editorial-chip px-3 py-1 text-[11px] font-semibold">Open</span>
        </div>
        <span className="mt-5 inline-flex w-fit rounded-full bg-[color:var(--surface-low)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--text-soft)]">
          {agentLabel}
        </span>
        <p className="mt-4 text-sm leading-7 text-[color:var(--text-muted)]">{agent.description}</p>
        <div className="mt-auto flex items-center justify-between pt-8 text-sm font-semibold text-[color:var(--primary)]">
          <span>{content.cta}</span>
          <span className="transition group-hover:translate-x-1">Open studio</span>
        </div>
      </div>
    </Link>
  );
}
