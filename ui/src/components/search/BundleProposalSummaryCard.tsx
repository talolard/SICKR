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
    ? "mt-3 max-h-24 overflow-y-auto rounded-2xl border border-slate-200 bg-white px-3 py-2 pr-2 text-sm leading-6 text-slate-700"
    : "mt-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm leading-6 text-slate-700";
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
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Bundle proposal
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold tracking-tight text-slate-950">{proposal.title}</h3>
          <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600">
            {proposal.items.length} {proposal.items.length === 1 ? "item" : "items"}
          </span>
          {highlighted ? (
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-900">
              Selected
            </span>
          ) : null}
          {proposal.budget_cap_eur !== null ? (
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600">
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
              <p className="mt-1 text-[11px] text-slate-500">Scroll to read the full explanation.</p>
            ) : null}
          </div>
        ) : null}
      </div>
      <div className="shrink-0 rounded-[20px] border border-slate-200 bg-white px-3 py-3 text-right">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-slate-500">Total</p>
        <p className="mt-1 text-base font-semibold text-slate-950">
          {formatBundlePrice(proposal.bundle_total_eur)}
        </p>
        <p className="mt-1 text-[11px] text-slate-500">{formatBundleCreatedAt(proposal.created_at)}</p>
        <div className="mt-3 flex items-center justify-end gap-2">
          <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-600">
            {expanded ? "-" : "+"}
          </span>
          <p className="text-xs font-semibold text-slate-700">{actionLabel}</p>
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
    "group w-full rounded-[24px] border p-4 text-left transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400",
    highlighted
      ? "border-slate-900 bg-slate-50 ring-1 ring-amber-200"
      : "border-slate-200 bg-slate-50/70",
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
      className={`${className} cursor-pointer hover:border-slate-300 hover:bg-white hover:shadow-sm`}
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
