"use client";

import Image from "next/image";
import Link from "next/link";

import type { AgentItem } from "@/lib/agents";
import { formatAgentName } from "@/lib/agentLabels";

type AgentLauncherCardProps = {
  agent: AgentItem;
};

type AgentStudioCardContent = {
  headline: string;
  summary: string;
  cta: string;
  imageSrc: string;
  imageAlt: string;
  accent: "forest" | "terracotta" | "stone";
};

function getAgentStudioCardContent(agentName: string): AgentStudioCardContent {
  switch (agentName) {
    case "search":
      return {
        headline: "Find the right pieces for your space",
        summary: "Discover furniture that solves the room problem without losing the mood.",
        cta: "Start Designing",
        imageSrc: "/stitch/search-studio.svg",
        imageAlt: "Warm editorial illustration of a curated sofa and lighting setup.",
        accent: "forest",
      };
    case "floor_plan_intake":
      return {
        headline: "Plan your room with confidence",
        summary: "Map the space first so layout and scale feel deliberate before you buy.",
        cta: "Begin Planning",
        imageSrc: "/stitch/floor-plan-studio.svg",
        imageAlt: "Soft architectural floor plan illustration on warm paper tones.",
        accent: "terracotta",
      };
    case "image_analysis":
      return {
        headline: "Get design guidance from your space",
        summary: "Read the room through a photo and pull out styling opportunities quickly.",
        cta: "Get Guidance",
        imageSrc: "/stitch/image-studio.svg",
        imageAlt: "Editorial room-scene illustration for image-led design guidance.",
        accent: "stone",
      };
    default:
      return {
        headline: `Open ${formatAgentName(agentName)}`,
        summary: "Step into a focused workspace built for a specific interior-design task.",
        cta: "Open Workspace",
        imageSrc: "/stitch/search-studio.svg",
        imageAlt: "Editorial workspace illustration.",
        accent: "forest",
      };
  }
}

function AgentAccentGlyph({ accent }: { accent: AgentStudioCardContent["accent"] }): React.ReactElement {
  if (accent === "terracotta") {
    return (
      <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 20 20">
        <path
          d="M6 16V6.8l4-2.8 4 2.8V16"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.5"
        />
        <path d="M10 8v8" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
      </svg>
    );
  }

  if (accent === "stone") {
    return (
      <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 20 20">
        <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
        <path
          d="M10 3.5V5.5M10 14.5v2M3.5 10H5.5M14.5 10h2M5.3 5.3l1.4 1.4M13.3 13.3l1.4 1.4M14.7 5.3l-1.4 1.4M6.7 13.3l-1.4 1.4"
          stroke="currentColor"
          strokeLinecap="round"
          strokeWidth="1.5"
        />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 20 20">
      <path
        d="M6.3 15v-3.8c0-2.1 1.6-3.7 3.7-3.7h1.6c1.2 0 2.3.6 3 1.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <path
        d="M4.5 15h11"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <path
        d="M14 4.8c.8.8 1.3 2 1.3 3.2"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

function accentCircleClass(accent: AgentStudioCardContent["accent"]): string {
  switch (accent) {
    case "terracotta":
      return "bg-[color:var(--secondary-container)] text-[color:var(--secondary)]";
    case "stone":
      return "bg-[color:var(--primary-container)] text-white";
    default:
      return "bg-[color:var(--primary-container)] text-white";
  }
}

function ArrowGlyph(): React.ReactElement {
  return (
    <svg aria-hidden="true" className="h-4 w-4 transition group-hover:translate-x-0.5" fill="none" viewBox="0 0 20 20">
      <path
        d="M5 10h9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.5"
      />
      <path
        d="M10.5 5.5 15 10l-4.5 4.5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  );
}

export function AgentLauncherCard({
  agent,
}: AgentLauncherCardProps): React.ReactElement {
  const content = getAgentStudioCardContent(agent.name);
  const agentLabel = formatAgentName(agent.name);

  return (
    <Link
      aria-label={`${agentLabel} workspace. ${content.headline}`}
      className="group editorial-card flex h-full flex-col overflow-hidden rounded-[32px] transition hover:-translate-y-1 hover:shadow-[0_50px_90px_rgba(32,27,16,0.12)]"
      href={`/agents/${agent.name}`}
    >
      <div className="relative h-52 overflow-hidden bg-surface-container-low">
        <Image
          alt={content.imageAlt}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
          height={420}
          priority={false}
          src={content.imageSrc}
          width={640}
        />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(32,27,16,0.02)_0%,rgba(32,27,16,0.12)_100%)]" />
      </div>
      <div className="flex flex-1 flex-col bg-[linear-gradient(180deg,var(--surface-container-lowest)_0%,#fbf2e4_100%)] px-6 pb-6 pt-5">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-full shadow-[0_16px_30px_rgba(32,27,16,0.12)] ${accentCircleClass(content.accent)}`}
        >
          <AgentAccentGlyph accent={content.accent} />
        </div>
        <h3 className="editorial-display mt-5 max-w-[15rem] text-[2rem] leading-[0.96] text-primary">
          {content.headline}
        </h3>
        <p className="editorial-body-copy mt-4 max-w-[16rem] text-sm leading-6">
          {content.summary}
        </p>
        <span className="mt-auto inline-flex items-center gap-2 pt-6 text-sm font-semibold text-primary">
          <span>{content.cta}</span>
          <ArrowGlyph />
        </span>
      </div>
    </Link>
  );
}
