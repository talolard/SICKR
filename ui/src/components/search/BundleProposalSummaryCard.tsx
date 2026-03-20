"use client";

import type { ReactElement } from "react";

import type { BundleProposal } from "@/lib/bundleProposalsStore";

const LONG_NOTES_THRESHOLD = 160;

export function bundleSummaryCardId(bundleId: string): string {
  return `bundle-summary-${bundleId}`;
}

export function formatBundlePrice(value: number | null): string {
  return value === null ? "—" : `€${value.toFixed(2)}`;
}

export function formatBundleCreatedAt(value: string): string {
  return new Date(value).toLocaleString();
}

type BundleProposalSummaryCardProps = {
  proposal: BundleProposal;
  actionLabel: string;
  expanded?: boolean;
  highlighted?: boolean;
  onClick?: (() => void) | undefined;
};

function noteContainerClassName(hasLongNotes: boolean): string {
  return hasLongNotes
    ? "mt-3 max-h-24 overflow-y-auto rounded-[22px] bg-[color:var(--surface-container-lowest)] px-3 py-3 pr-2 text-sm leading-6 text-on-surface"
    : "mt-3 rounded-[22px] bg-[color:var(--surface-container-lowest)] px-3 py-3 text-sm leading-6 text-on-surface";
}

function SummaryCardContent({
  actionLabel,
  expanded = false,
  highlighted = false,
  proposal,
}: Omit<BundleProposalSummaryCardProps, "onClick">): ReactElement {
  const hasLongNotes = (proposal.notes?.length ?? 0) > LONG_NOTES_THRESHOLD;

  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0 flex-1">
        <p className="editorial-eyebrow">
          Bundle proposal
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold tracking-tight text-primary">{proposal.title}</h3>
          <span className="rounded-full bg-[color:var(--surface-container-lowest)] px-2.5 py-1 text-[11px] font-medium text-on-surface-variant">
            {proposal.items.length} {proposal.items.length === 1 ? "item" : "items"}
          </span>
          {highlighted ? (
            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-900">
              Selected
            </span>
          ) : null}
          {proposal.budget_cap_eur !== null ? (
            <span className="rounded-full bg-[color:var(--surface-container-high)] px-2.5 py-1 text-[11px] font-medium text-on-surface-variant">
              Budget {formatBundlePrice(proposal.budget_cap_eur)}
            </span>
          ) : null}
        </div>
        {proposal.notes ? (
          <div>
            <div className={noteContainerClassName(hasLongNotes)} data-testid="bundle-summary-notes">
              {proposal.notes}
            </div>
            {hasLongNotes ? (
              <p className="mt-1 text-[11px] text-on-surface-variant">
                Scroll to read the full explanation.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="shrink-0 rounded-[22px] bg-[color:var(--surface-container-lowest)] px-3 py-3 text-right shadow-[var(--panel-shadow)]">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-on-surface-variant">
          Total
        </p>
        <p className="mt-1 text-base font-semibold text-primary">
          {formatBundlePrice(proposal.bundle_total_eur)}
        </p>
        <p className="mt-1 text-[11px] text-on-surface-variant">
          {formatBundleCreatedAt(proposal.created_at)}
        </p>
        <div className="mt-3 flex items-center justify-end gap-2">
          <span className="rounded-full bg-[color:var(--surface-container-high)] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
            {expanded ? "-" : "+"}
          </span>
          <p className="text-xs font-semibold text-on-surface">{actionLabel}</p>
        </div>
      </div>
    </div>
  );
}

export function BundleProposalSummaryCard({
  actionLabel,
  expanded = false,
  highlighted = false,
  onClick,
  proposal,
}: BundleProposalSummaryCardProps): ReactElement {
  const cardId = bundleSummaryCardId(proposal.bundle_id);
  const className = [
    "group w-full rounded-[26px] p-4 text-left transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(24,36,27,0.2)]",
    highlighted
      ? "bg-[color:var(--surface-container-high)]"
      : "bg-[color:var(--surface-container-low)]",
  ].join(" ");

  if (!onClick) {
    return (
      <div className={className} id={cardId}>
        <SummaryCardContent
          actionLabel={actionLabel}
          expanded={expanded}
          highlighted={highlighted}
          proposal={proposal}
        />
      </div>
    );
  }

  return (
    <button
      aria-controls={`${cardId}-details`}
      aria-expanded={expanded}
      className={`${className} cursor-pointer hover:bg-[color:var(--surface-container-high)]`}
      id={cardId}
      onClick={onClick}
      type="button"
    >
      <SummaryCardContent
        actionLabel={actionLabel}
        expanded={expanded}
        highlighted={highlighted}
        proposal={proposal}
      />
    </button>
  );
}
