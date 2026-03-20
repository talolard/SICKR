"use client";

import { AgentLauncherCard } from "@/components/agents/AgentLauncherCard";
import type { AgentItem } from "@/lib/agents";

type StudioShowcaseLayoutProps = {
  eyebrow: string;
  title: string;
  description: string;
  agents: AgentItem[];
  error: string;
  isLoadingAgents: boolean;
};

type RailGlyphKind =
  | "chat"
  | "help"
  | "history"
  | "info"
  | "light"
  | "materials"
  | "payments"
  | "preference";

type RailItem = {
  label: string;
  icon: RailGlyphKind;
  active?: boolean;
};

type ArchiveProject = {
  category: string;
  lastEdited: string;
  status: "active" | "finalized";
  summary: string;
  thumbnail: "lighting" | "living";
  title: string;
};

const contextItems: readonly RailItem[] = [
  { label: "Room Facts", icon: "info", active: true },
  { label: "Preferences", icon: "preference" },
  { label: "Budget", icon: "payments" },
  { label: "Materials", icon: "materials" },
];

const consultationItems: readonly RailItem[] = [
  { label: "Chat", icon: "chat", active: true },
  { label: "Suggestions", icon: "light" },
  { label: "History", icon: "history" },
];

const archiveProjects: readonly ArchiveProject[] = [
  {
    category: "Residential",
    lastEdited: "Last edited 2d ago",
    status: "active",
    summary: "Focusing on non-permanent luxury, vertical storage, and gentle tonal contrast.",
    thumbnail: "living",
    title: "Small Rental Living Room",
  },
  {
    category: "Atmosphere",
    lastEdited: "Last edited 5d ago",
    status: "finalized",
    summary: "Atmospheric layering for evening reading, softened shadows, and calmer wake-up light.",
    thumbnail: "lighting",
    title: "Bedroom Lighting Update",
  },
];

const showcaseAgentOrder: Readonly<Record<string, number>> = {
  search: 0,
  floor_plan_intake: 1,
  image_analysis: 2,
};

function orderShowcaseAgents(agents: readonly AgentItem[]): AgentItem[] {
  return [...agents].sort((left, right) => {
    const leftOrder = showcaseAgentOrder[left.name] ?? Number.MAX_SAFE_INTEGER;
    const rightOrder = showcaseAgentOrder[right.name] ?? Number.MAX_SAFE_INTEGER;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.name.localeCompare(right.name);
  });
}

function contextItemClass(active: boolean): string {
  return [
    "flex w-full items-center gap-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] transition",
    active
      ? "-ml-8 rounded-r-full bg-[color:var(--surface-container-lowest)] py-3.5 pl-8 pr-6 text-primary shadow-[0_12px_24px_rgba(32,27,16,0.06)]"
      : "px-0 py-3.5 text-on-surface-variant hover:translate-x-1 hover:text-primary",
  ].join(" ");
}

function consultationItemClass(active: boolean): string {
  return [
    "flex w-full items-center gap-3 px-0 py-3 text-left text-sm transition",
    active
      ? "font-semibold text-primary"
      : "text-on-surface-variant hover:translate-x-1 hover:text-primary",
  ].join(" ");
}

function railGlyphShellClass(active: boolean): string {
  return active
    ? "flex h-5 w-5 items-center justify-center text-primary"
    : "flex h-5 w-5 items-center justify-center text-[color:color-mix(in_srgb,var(--on-surface-variant)_78%,transparent)]";
}

function RailGlyph({ kind }: { kind: RailGlyphKind }): React.ReactElement {
  switch (kind) {
    case "chat":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M4 5.5A2.5 2.5 0 0 1 6.5 3h7A2.5 2.5 0 0 1 16 5.5v4A2.5 2.5 0 0 1 13.5 12H9l-3.5 3v-3H6.5A2.5 2.5 0 0 1 4 9.5z"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.3"
          />
        </svg>
      );
    case "help":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M10 14.8h.01M7.9 7.4a2.2 2.2 0 1 1 3.6 1.7c-.8.6-1.3 1-1.3 2"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.3"
          />
          <circle cx="10" cy="10" r="6.7" stroke="currentColor" strokeWidth="1.3" />
        </svg>
      );
    case "history":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M4.8 9.3A5.3 5.3 0 1 1 10 15.2a5.2 5.2 0 0 1-4.7-2.9"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.3"
          />
          <path d="M4.4 4.7v4h4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.3" />
          <path d="M10 6.7v3l2.2 1.4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.3" />
        </svg>
      );
    case "light":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M10 3.2a4 4 0 0 0-2.8 6.9c.6.6.9 1.3 1 2h3.6c.1-.7.4-1.4 1-2A4 4 0 0 0 10 3.2Z"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.3"
          />
          <path d="M8.6 14h2.8M8.9 16h2.2" stroke="currentColor" strokeLinecap="round" strokeWidth="1.3" />
        </svg>
      );
    case "materials":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M5.1 8.1 11.9 14.9M8.3 4.9l6.8 6.8M4.7 11.7l3.6 3.6"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.2"
          />
        </svg>
      );
    case "payments":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <rect
            height="10.4"
            rx="1.8"
            stroke="currentColor"
            strokeWidth="1.2"
            width="12"
            x="4"
            y="4.8"
          />
          <path d="M4.7 8.1h10.6M7.7 11.6h3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.2" />
        </svg>
      );
    case "preference":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M10 15.6s-4.8-2.8-4.8-6.6a2.8 2.8 0 0 1 5-1.8 2.8 2.8 0 0 1 5 1.8c0 3.8-5.2 6.6-5.2 6.6Z"
            stroke="currentColor"
            strokeLinejoin="round"
            strokeWidth="1.3"
          />
        </svg>
      );
    case "info":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="6.7" stroke="currentColor" strokeWidth="1.3" />
          <path d="M10 8.3v4M10 6.1h.01" stroke="currentColor" strokeLinecap="round" strokeWidth="1.3" />
        </svg>
      );
  }
}

function SparkGlyph(): React.ReactElement {
  return (
    <svg aria-hidden="true" className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
      <path d="M10 2.8 11.7 7 16 8.7l-4.3 1.7L10 14.6l-1.7-4.2L4 8.7 8.3 7z" />
    </svg>
  );
}

function ArchiveGlyph({ kind }: { kind: ArchiveProject["thumbnail"] }): React.ReactElement {
  if (kind === "lighting") {
    return (
      <svg aria-hidden="true" className="h-10 w-10" fill="none" viewBox="0 0 40 40">
        <path
          d="M20 8a7.8 7.8 0 0 0-5.3 13.5c1.1 1 1.7 2.1 1.9 3.2h6.8c.2-1.1.8-2.2 1.9-3.2A7.8 7.8 0 0 0 20 8Z"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.6"
        />
        <path d="M17.5 28.2h5M18 31h4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.6" />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" className="h-10 w-10" fill="none" viewBox="0 0 40 40">
      <path
        d="M9 24.5a11 11 0 1 0 22 0"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.8"
      />
      <path
        d="M20 11v13l5.5-3.4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
    </svg>
  );
}

function archiveTileClass(kind: ArchiveProject["thumbnail"]): string {
  if (kind === "lighting") {
    return "bg-[color:var(--surface-container-high)] text-[color:var(--surface-tint)]";
  }
  return "bg-[color:var(--primary-container)] text-[#f4eadc]";
}

function archiveStatusClass(status: ArchiveProject["status"]): string {
  if (status === "finalized") {
    return "bg-[color:var(--surface-tint)]";
  }
  return "bg-[#2f6b45]";
}

function ArchiveProjectCard({ project }: { project: ArchiveProject }): React.ReactElement {
  return (
    <article className="grid grid-cols-[112px_minmax(0,1fr)] gap-5">
      <div
        className={`flex h-[112px] items-center justify-center rounded-[28px] shadow-[0_18px_34px_rgba(32,27,16,0.06)] ${archiveTileClass(project.thumbnail)}`}
      >
        <ArchiveGlyph kind={project.thumbnail} />
      </div>
      <div className="pt-1">
        <p className="editorial-display text-sm italic text-[color:var(--secondary)]">
          {project.category}
        </p>
        <h3 className="mt-1 text-[1.75rem] font-semibold leading-[1.05] tracking-tight text-[color:var(--primary)]">
          {project.title}
        </h3>
        <p className="editorial-body-copy mt-2 max-w-[21rem] text-sm leading-6">
          {project.summary}
        </p>
        <div className="editorial-meta-copy mt-3 flex flex-wrap items-center gap-4 text-[11px] font-semibold uppercase tracking-[0.16em]">
          <span>{project.lastEdited}</span>
          <span className="inline-flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${archiveStatusClass(project.status)}`} />
            <span>{project.status}</span>
          </span>
        </div>
      </div>
    </article>
  );
}

export function StudioShowcaseLayout({
  eyebrow,
  title,
  description,
  agents,
  error,
  isLoadingAgents,
}: StudioShowcaseLayoutProps): React.ReactElement {
  const orderedAgents = orderShowcaseAgents(agents);

  return (
    <section className="mx-auto grid w-full max-w-[1440px] gap-0 px-0 pb-16 pt-0 lg:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)_312px]">
      <aside
        className="hidden bg-[color:var(--surface-container-low)] lg:sticky lg:top-16 lg:flex lg:h-[calc(100vh-4rem)] lg:min-h-[44rem] lg:flex-col lg:justify-between lg:self-start lg:px-8 lg:py-8"
        data-testid="studio-showcase-left-rail"
      >
        <div>
          <h2 className="editorial-display text-3xl text-[color:var(--primary)]">Context</h2>
          <p className="editorial-meta-copy mt-2 text-[10px] font-semibold uppercase tracking-[0.22em]">
            Project Specifications
          </p>
        </div>
        <nav className="flex flex-col gap-0">
          {contextItems.map((item) => (
            <button
              className={contextItemClass(Boolean(item.active))}
              key={item.label}
              type="button"
            >
              <span className={railGlyphShellClass(Boolean(item.active))}>
                <RailGlyph kind={item.icon} />
              </span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button
          className="editorial-button-primary w-full rounded-[18px] px-5 py-4 text-sm font-semibold"
          type="button"
        >
          Update Brief
        </button>
      </aside>

      <section className="min-w-0 px-4 pt-8 md:px-6 lg:px-8" data-testid="studio-showcase-main">
        <header>
          <p className="editorial-eyebrow">{eyebrow}</p>
          <h1 className="editorial-display mt-4 max-w-4xl text-5xl leading-[0.92] text-on-surface md:text-7xl">
            {title}
          </h1>
          <p className="editorial-body-copy mt-5 max-w-2xl text-lg leading-8">
            {description}
          </p>
        </header>

        {error ? (
          <p className="mt-6 rounded-[22px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
        ) : null}

        <div className="mt-9 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {isLoadingAgents
            ? Array.from({ length: 3 }, (_, index) => (
                <div
                  className="editorial-card editorial-soft-pulse h-[26rem] rounded-[32px] bg-surface-container-lowest"
                  key={`agent-loading-${index}`}
                />
              ))
            : orderedAgents.map((agent) => (
                <div className="h-full" key={agent.name}>
                  <AgentLauncherCard agent={agent} />
                </div>
              ))}
        </div>

        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <span className="editorial-chip px-5 py-2.5 text-sm font-medium">Compare Fabrics</span>
          <span className="editorial-chip px-5 py-2.5 text-sm font-medium">Lighting Modes</span>
        </div>

        <section className="mt-16" id="archives">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="editorial-eyebrow">The Archives</p>
              <h2 className="editorial-display mt-3 text-4xl text-[color:var(--primary)]">
                Recent Projects
              </h2>
            </div>
            <button
              className="editorial-tertiary-action"
              type="button"
            >
              View All Archives
            </button>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-8 md:grid-cols-2">
            {archiveProjects.map((project) => (
              <ArchiveProjectCard key={project.title} project={project} />
            ))}
          </div>
        </section>
      </section>

      <aside
        className="hidden bg-[color:var(--surface-container-lowest)] xl:sticky xl:top-16 xl:flex xl:h-[calc(100vh-4rem)] xl:min-h-[44rem] xl:flex-col xl:self-start xl:px-7 xl:py-8"
        data-testid="studio-showcase-right-rail"
      >
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[color:var(--primary)] text-white shadow-[0_18px_34px_rgba(24,36,27,0.18)]">
              <SparkGlyph />
            </div>
            <div>
              <h2 className="text-base font-semibold text-[color:var(--primary)]">
                Design Consultation
              </h2>
              <p className="editorial-meta-copy mt-1 text-[11px] font-semibold uppercase tracking-[0.18em]">
                AI Assistant Active
              </p>
            </div>
          </div>

          <div className="editorial-body-copy mt-5 rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4 text-sm leading-7">
            I&apos;ve noticed your preference for Belgian linen. Would you like me to curate some
            matching textures for the living room?
          </div>
        </div>

        <div className="mt-9 flex flex-col gap-1">
          {consultationItems.map((item) => (
            <button
              className={consultationItemClass(Boolean(item.active))}
              key={item.label}
              type="button"
            >
              <span className="flex items-center gap-3">
                <span className={railGlyphShellClass(Boolean(item.active))}>
                  <RailGlyph kind={item.icon} />
                </span>
                <span className="text-sm font-semibold">{item.label}</span>
              </span>
            </button>
          ))}
        </div>

        <div className="editorial-subtle-separator mt-auto h-px w-full" />
        <button className="mt-5 flex items-center gap-3 px-0 pb-0 pt-5 text-left text-sm text-on-surface-variant" type="button">
          <span className={railGlyphShellClass(false)}>
            <RailGlyph kind="help" />
          </span>
          <span className="font-medium">Help &amp; Resources</span>
        </button>
      </aside>
    </section>
  );
}
