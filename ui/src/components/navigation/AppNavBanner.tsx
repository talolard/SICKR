"use client";

import { useRef } from "react";
import { usePathname, useRouter } from "next/navigation";

import type { AgentItem } from "@/lib/agents";
import { describeAgentCapability, formatAgentName } from "@/lib/agentLabels";

type AppNavBannerProps = {
  currentAgentName: string | null;
  agents: AgentItem[];
  isLoadingAgents?: boolean;
  agentLoadError?: string | null;
};

type HomeNavItem = {
  destination: "gallery" | "history" | "my-designs";
  label: string;
  path: string;
};

const homeNavItems: readonly HomeNavItem[] = [
  { destination: "my-designs", label: "My Designs", path: "/" },
  { destination: "gallery", label: "Gallery", path: "/agents" },
  { destination: "history", label: "History", path: "/#archives" },
];

function HeaderGlyph({ kind }: { kind: "bell" | "settings" }): React.ReactElement {
  if (kind === "bell") {
    return (
      <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
        <path
          d="M10 3.5c-2.1 0-3.8 1.7-3.8 3.8v1.5c0 .9-.3 1.8-.8 2.5l-.7 1h10.6l-.7-1c-.5-.7-.8-1.6-.8-2.5V7.3A3.8 3.8 0 0 0 10 3.5Z"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.2"
        />
        <path
          d="M8.5 14.4a1.7 1.7 0 0 0 3 0"
          stroke="currentColor"
          strokeLinecap="round"
          strokeWidth="1.2"
        />
      </svg>
    );
  }

  return (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 20 20">
      <path
        d="M10 3.9v1.3M10 14.8v1.3M5.2 10H3.9M16.1 10h-1.3M6.2 6.2l-.9-.9M14.7 14.7l-.9-.9M13.8 6.2l.9-.9M5.3 14.7l.9-.9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.2"
      />
      <circle cx="10" cy="10" r="2.6" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

export function AppNavBanner({
  currentAgentName,
  agents,
  isLoadingAgents = false,
  agentLoadError = null,
}: AppNavBannerProps): React.ReactElement {
  const pathname = usePathname();
  const router = useRouter();
  const launcherRef = useRef<HTMLDetailsElement | null>(null);
  const currentAgentLabel = currentAgentName ? formatAgentName(currentAgentName) : "Studios";
  const launcherDisabled = isLoadingAgents || (agents.length === 0 && !agentLoadError);
  const activeNav = pathname.startsWith("/agents") ? "gallery" : "my-designs";

  function navigateTo(nextPath: string): void {
    launcherRef.current?.removeAttribute("open");
    router.push(nextPath);
  }

  function launcherOptionClass(active: boolean): string {
    return [
      "flex w-full items-center justify-between rounded-[22px] px-4 py-3 text-left transition",
      active ? "editorial-launcher-option-active" : "editorial-launcher-option",
    ].join(" ");
  }

  function homeNavItemClass(active: boolean): string {
    return active
      ? "border-b-2 border-[color:var(--primary)] pb-1 text-sm font-semibold text-[color:var(--primary)]"
      : "editorial-quiet-copy pb-1 text-sm transition hover:text-[color:var(--primary)]";
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
            {homeNavItems.map((item) => (
              <button
                className={homeNavItemClass(item.destination === activeNav)}
                key={item.destination}
                onClick={() => navigateTo(item.path)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <button
            aria-label="Open notifications"
            className="editorial-nav-icon-button transition hover:-translate-y-0.5"
            onClick={() => navigateTo("/#archives")}
            type="button"
          >
            <HeaderGlyph kind="bell" />
          </button>
          <button
            aria-label="Open settings"
            className="editorial-nav-icon-button transition hover:-translate-y-0.5"
            onClick={() => launcherRef.current?.setAttribute("open", "")}
            type="button"
          >
            <HeaderGlyph kind="settings" />
          </button>

          {launcherDisabled ? (
            <div
              aria-disabled="true"
              className="editorial-launcher-shell px-4 py-2.5 text-left text-on-surface-variant"
              data-testid="app-nav-agent-launcher"
            >
              <span className="text-sm font-medium text-primary">Loading agent list...</span>
            </div>
          ) : (
            <details
              className="relative"
              data-testid="app-nav-agent-launcher"
              ref={launcherRef}
            >
              <summary
                aria-label="Open studio menu"
                className="editorial-launcher-shell cursor-pointer p-1.5"
                data-testid="app-nav-agent-launcher-trigger"
              >
                <div className="flex items-center pl-0.5 pr-0.5">
                  <div className="editorial-avatar flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold uppercase">
                    {currentAgentName ? currentAgentLabel.charAt(0) : "T"}
                  </div>
                </div>
              </summary>
              <div className="editorial-launcher-menu absolute right-0 z-30 mt-3 w-[22rem] rounded-[28px] p-3">
                {agentLoadError ? (
                  <p className="rounded-[20px] bg-red-50 px-3 py-2 text-xs text-red-700">
                    {agentLoadError}
                  </p>
                ) : null}
                <div className="px-2 pb-2">
                  <p className="editorial-eyebrow">Studio Menu</p>
                  <p className="mt-2 text-sm font-semibold text-primary">
                    {currentAgentName ? currentAgentLabel : "Choose a workspace"}
                  </p>
                  <p className="mt-1 text-xs text-on-surface-variant">
                    {agents.length} workspace{agents.length === 1 ? "" : "s"} available
                  </p>
                </div>
                <button
                  className={launcherOptionClass(currentAgentName === null)}
                  onClick={() => navigateTo("/")}
                  type="button"
                >
                  <span>
                    <span className="block text-sm font-semibold">Home</span>
                    <span
                      className={`mt-1 block text-xs ${
                        currentAgentName === null ? "text-white/75" : "text-on-surface-variant"
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
                        className={launcherOptionClass(active)}
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
                              active ? "text-white/75" : "text-on-surface-variant"
                            }`}
                          >
                            {describeAgentCapability(agent.name)}
                          </span>
                        </span>
                        <span
                          className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                            active
                              ? "bg-white/14 text-white"
                              : "bg-tertiary-fixed text-on-surface"
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
