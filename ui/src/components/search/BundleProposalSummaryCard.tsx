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
    ? "mt-2 max-h-20 overflow-y-auto pr-2 text-[13px] leading-5 text-on-surface-variant"
    : "mt-2 text-[13px] leading-5 text-on-surface-variant";
}

function SummaryCardContent({
  actionLabel,
  expanded = false,
  highlighted = false,
  proposal,
}: Omit<BundleProposalSummaryCardProps, "onClick">): ReactElement {
  const hasLongNotes = (proposal.notes?.length ?? 0) > LONG_NOTES_THRESHOLD;

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant">
          Bundle proposal
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          <h3 className="text-[15px] font-semibold leading-5 tracking-tight text-primary">
            {proposal.title}
          </h3>
          <span className="rounded-full bg-[color:var(--surface-container-lowest)] px-2 py-0.5 text-[10px] font-medium text-on-surface-variant">
            {proposal.items.length} {proposal.items.length === 1 ? "item" : "items"}
          </span>
          {highlighted ? (
            <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-900">
              Selected
            </span>
          ) : null}
          {proposal.budget_cap_eur !== null ? (
            <span className="rounded-full bg-[color:var(--surface-container-high)] px-2 py-0.5 text-[10px] font-medium text-on-surface-variant">
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
              <p className="mt-1 text-[10px] text-on-surface-variant">
                Scroll to read the full rationale.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="shrink-0 rounded-[18px] bg-[color:var(--surface-container-lowest)] px-3 py-2.5 text-right shadow-[var(--panel-shadow)] lg:min-w-[132px]">
        <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-on-surface-variant">
          Total
        </p>
        <p className="mt-1 text-[1.05rem] font-semibold leading-5 text-primary">
          {formatBundlePrice(proposal.bundle_total_eur)}
        </p>
        <p className="mt-1 text-[10px] leading-4 text-on-surface-variant">
          {formatBundleCreatedAt(proposal.created_at)}
        </p>
        <div className="mt-2.5 flex items-center justify-end gap-1.5">
          <span className="rounded-full bg-[color:var(--surface-container-high)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
            {expanded ? "-" : "+"}
          </span>
          <p className="text-[11px] font-semibold text-on-surface">{actionLabel}</p>
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
    "group w-full rounded-[24px] p-3.5 text-left transition-colors",
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
