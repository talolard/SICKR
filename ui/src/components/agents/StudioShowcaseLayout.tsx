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
          <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--text-soft)]">
            Project Specifications
          </p>
        </div>
        <nav className="space-y-2">
          {["Room Facts", "Preferences", "Budget", "Materials"].map((label, index) => (
            <div
              className={`rounded-full px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] ${
                index === 0
                  ? "bg-[color:var(--surface-lowest)] text-[color:var(--primary)] shadow-[0_14px_30px_rgba(32,27,16,0.08)]"
                  : "text-[color:var(--text-soft)]"
              }`}
              key={label}
            >
              {label}
            </div>
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
          <h1 className="editorial-display mt-4 max-w-4xl text-5xl leading-[0.92] text-[color:var(--text-primary)] md:text-7xl">
            {title}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[color:var(--text-muted)]">
            {description}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <span className="editorial-chip px-5 py-2.5 text-sm font-medium">Compare Fabrics</span>
            <span className="editorial-chip px-5 py-2.5 text-sm font-medium">Lighting Moods</span>
          </div>
        </header>

        {error ? (
          <p className="mt-6 rounded-[22px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
        ) : null}

        <div className="mt-10 grid grid-cols-1 gap-6 xl:grid-cols-3">
          {isLoadingAgents
            ? Array.from({ length: 3 }, (_, index) => (
                <div
                  className="editorial-card editorial-soft-pulse h-[26rem] rounded-[32px] bg-[color:var(--surface-lowest)]"
                  key={`agent-loading-${index}`}
                />
              ))
            : agents.map((agent) => <AgentLauncherCard agent={agent} key={agent.name} />)}
        </div>

        <section className="mt-16">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="editorial-eyebrow">The Archives</p>
              <h2 className="editorial-display mt-3 text-4xl text-[color:var(--primary)]">
                Recent Projects
              </h2>
            </div>
            <button
              className="border-b border-[color:var(--outline-ghost)] pb-1 text-sm font-semibold text-[color:var(--primary)]"
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
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">
                  Focusing on non-permanent luxury, vertical storage, and gentle tonal contrast.
                </p>
                <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-soft)]">
                  Last edited 2d ago
                </p>
              </div>
            </article>

            <article className="grid grid-cols-[88px_minmax(0,1fr)] gap-5">
              <div className="flex h-[88px] items-center justify-center rounded-[24px] bg-[color:var(--surface-high)] text-sm font-semibold uppercase tracking-[0.2em] text-[color:var(--primary)]">
                Mood
              </div>
              <div>
                <p className="editorial-display text-sm italic text-[color:var(--secondary)]">
                  Atmosphere
                </p>
                <h3 className="mt-1 text-2xl font-semibold tracking-tight text-[color:var(--primary)]">
                  Bedroom Lighting Update
                </h3>
                <p className="mt-2 text-sm leading-6 text-[color:var(--text-muted)]">
                  Atmospheric layering for evening reading, softened shadows, and calmer wake-up light.
                </p>
                <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-soft)]">
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
              <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--text-soft)]">
                AI Assistant Active
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-[24px] bg-[color:var(--surface-lowest)] px-4 py-5 text-sm leading-7 text-[color:var(--text-muted)] shadow-[0_14px_28px_rgba(32,27,16,0.06)]">
            I&apos;ve noticed your preference for Belgian linen and quiet forest tones. Would you
            like me to curate matching textures for the living room?
          </div>
        </div>

        <div className="mt-10 space-y-5">
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--primary)]">Chat</h3>
            <div className="mt-3 rounded-full bg-[color:var(--secondary-container)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:#5b3612]">
              New
            </div>
          </div>
          <p className="text-sm text-[color:var(--text-soft)]">Suggestions</p>
          <p className="text-sm text-[color:var(--text-soft)]">History</p>
        </div>

        <div className="mt-auto border-t border-[color:var(--outline-ghost)] pt-5 text-sm text-[color:var(--text-soft)]">
          Help &amp; Resources
        </div>
      </aside>
    </section>
  );
}
