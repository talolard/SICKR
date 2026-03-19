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
  badge?: string;
};

const contextItems: RailItem[] = [
  { label: "Room Facts", icon: "info", active: true },
  { label: "Preferences", icon: "preference" },
  { label: "Budget", icon: "payments" },
  { label: "Materials", icon: "materials" },
];

const consultationItems: RailItem[] = [
  { label: "Chat", icon: "chat", active: true, badge: "New" },
  { label: "Suggestions", icon: "light" },
  { label: "History", icon: "history" },
];

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
            strokeWidth="1.4"
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
            strokeWidth="1.4"
          />
          <circle cx="10" cy="10" r="6.7" stroke="currentColor" strokeWidth="1.4" />
        </svg>
      );
    case "history":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M4.8 9.3A5.3 5.3 0 1 1 10 15.2a5.2 5.2 0 0 1-4.7-2.9"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.4"
          />
          <path d="M4.4 4.7v4h4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
          <path d="M10 6.7v3l2.2 1.4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
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
            strokeWidth="1.4"
          />
          <path d="M8.6 14h2.8M8.9 16h2.2" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
        </svg>
      );
    case "materials":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M5 5.5h10M5 10h10M5 14.5h10M6.5 4v12M10 4v12M13.5 4v12"
            stroke="currentColor"
            strokeLinecap="round"
            strokeWidth="1.3"
          />
        </svg>
      );
    case "payments":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M4 6.2c0-.9.7-1.7 1.7-1.7h8.6c.9 0 1.7.8 1.7 1.7v7.6c0 .9-.8 1.7-1.7 1.7H5.7c-1 0-1.7-.8-1.7-1.7z"
            stroke="currentColor"
            strokeWidth="1.4"
          />
          <path d="M4.5 8.2h11" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
          <path d="M8.2 12.4h2.5" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
        </svg>
      );
    case "preference":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <path
            d="M10 15.6s-4.8-2.8-4.8-6.6a2.8 2.8 0 0 1 5-1.8 2.8 2.8 0 0 1 5 1.8c0 3.8-5.2 6.6-5.2 6.6Z"
            stroke="currentColor"
            strokeLinejoin="round"
            strokeWidth="1.4"
          />
        </svg>
      );
    case "info":
      return (
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="6.7" stroke="currentColor" strokeWidth="1.4" />
          <path d="M10 8.3v4M10 6.1h.01" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
        </svg>
      );
  }
}

export function StudioShowcaseLayout({
  eyebrow,
  title,
  description,
  agents,
  error,
  isLoadingAgents,
}: StudioShowcaseLayoutProps): React.ReactElement {
  return (
    <section className="mx-auto grid w-full max-w-[1480px] gap-6 px-4 pb-16 pt-8 lg:grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[220px_minmax(0,1fr)_280px] xl:px-6">
      <aside className="editorial-panel hidden min-h-[calc(100vh-9rem)] flex-col justify-between rounded-[30px] px-6 py-8 lg:flex">
        <div>
          <h2 className="editorial-display text-3xl text-[color:var(--primary)]">Context</h2>
          <p className="editorial-meta-copy mt-2 text-[10px] font-semibold uppercase tracking-[0.22em]">
            Project Specifications
          </p>
        </div>
        <nav className="editorial-rail-list">
          {contextItems.map((item) => (
            <button
              className={`editorial-rail-item ${item.active ? "editorial-rail-item-active" : ""}`}
              key={item.label}
              type="button"
            >
              <span className="editorial-rail-glyph">
                <RailGlyph kind={item.icon} />
              </span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button
          className="editorial-button-primary w-full rounded-[20px] px-5 py-4 text-sm font-semibold"
          type="button"
        >
          Update Brief
        </button>
      </aside>

      <section className="min-w-0">
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

        <div className="mt-10 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.82fr)_minmax(0,1fr)] xl:items-start">
          {isLoadingAgents
            ? Array.from({ length: 3 }, (_, index) => (
                <div
                  className="editorial-card editorial-soft-pulse h-[26rem] rounded-[32px] bg-surface-container-lowest"
                  key={`agent-loading-${index}`}
                />
              ))
            : agents.map((agent, index) => (
                <div
                  className={
                    index === 1
                      ? "xl:translate-y-7"
                      : index === 2
                        ? "xl:-translate-y-3"
                        : ""
                  }
                  key={agent.name}
                >
                  <AgentLauncherCard agent={agent} />
                </div>
              ))}
        </div>

        <div className="mt-4 flex flex-wrap justify-center gap-3 xl:-ml-16">
          <span className="editorial-chip px-5 py-2.5 text-sm font-medium">Compare Fabrics</span>
          <span className="editorial-chip px-5 py-2.5 text-sm font-medium">Lighting Modes</span>
        </div>

        <section className="mt-14">
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
            <article className="grid grid-cols-[88px_minmax(0,1fr)] gap-5">
              <div className="flex h-[88px] items-center justify-center rounded-[24px] bg-[color:var(--primary-container)] text-sm font-semibold uppercase tracking-[0.2em] text-white">
                Living
              </div>
              <div>
                <p className="editorial-display text-sm italic text-[color:var(--secondary)]">
                  Residential
                </p>
                <h3 className="mt-1 text-2xl font-semibold tracking-tight text-[color:var(--primary)]">
                  Small Rental Living Room
                </h3>
                <p className="editorial-body-copy mt-2 text-sm leading-6">
                  Focusing on non-permanent luxury, vertical storage, and gentle tonal contrast.
                </p>
                <p className="editorial-meta-copy mt-3 text-[11px] font-semibold uppercase tracking-[0.18em]">
                  Last edited 2d ago
                </p>
              </div>
            </article>

            <article className="grid grid-cols-[88px_minmax(0,1fr)] gap-5">
              <div className="flex h-[88px] items-center justify-center rounded-[24px] bg-surface-container-high text-sm font-semibold uppercase tracking-[0.2em] text-primary">
                Mood
              </div>
              <div>
                <p className="editorial-display text-sm italic text-[color:var(--secondary)]">
                  Atmosphere
                </p>
                <h3 className="mt-1 text-2xl font-semibold tracking-tight text-[color:var(--primary)]">
                  Bedroom Lighting Update
                </h3>
                <p className="editorial-body-copy mt-2 text-sm leading-6">
                  Atmospheric layering for evening reading, softened shadows, and calmer wake-up light.
                </p>
                <p className="editorial-meta-copy mt-3 text-[11px] font-semibold uppercase tracking-[0.18em]">
                  Last edited 5d ago
                </p>
              </div>
            </article>
          </div>
        </section>
      </section>

      <aside className="editorial-panel hidden min-h-[calc(100vh-9rem)] flex-col rounded-[30px] px-6 py-8 xl:flex">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[color:var(--primary)] text-sm font-semibold text-white">
              AI
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

          <div className="editorial-note-card editorial-body-copy mt-6 rounded-[24px] px-4 py-5 text-sm leading-7">
            I&apos;ve noticed your preference for Belgian linen and quiet forest tones. Would you
            like me to curate matching textures for the living room?
          </div>
        </div>

        <div className="mt-10 editorial-rail-list">
          {consultationItems.map((item) => (
            <button
              className={`editorial-consultation-item ${
                item.active ? "editorial-consultation-item-active" : ""
              }`}
              key={item.label}
              type="button"
            >
              <span className="flex items-center gap-3">
                <span className="editorial-rail-glyph">
                  <RailGlyph kind={item.icon} />
                </span>
                <span className="text-sm font-semibold">{item.label}</span>
              </span>
              {item.badge ? <span className="editorial-status-pill">{item.badge}</span> : null}
            </button>
          ))}
        </div>

        <div className="editorial-subtle-separator mt-auto h-px w-full" />
        <button className="editorial-consultation-item mt-5 px-0 pb-0 pt-5" type="button">
          <span className="flex items-center gap-3">
            <span className="editorial-rail-glyph">
              <RailGlyph kind="help" />
            </span>
            <span className="text-sm font-medium">Help &amp; Resources</span>
          </span>
        </button>
      </aside>
    </section>
  );
}
