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
  highlighted?: boolean;
  onClick?: (() => void) | undefined;
};

function noteContainerClassName(hasLongNotes: boolean): string {
  return hasLongNotes
    ? "mt-2 max-h-24 overflow-y-auto rounded-md bg-white/80 px-3 py-2 pr-2 text-sm text-gray-700"
    : "mt-2 rounded-md bg-white/80 px-3 py-2 text-sm text-gray-700";
}

function SummaryCardContent({
  actionLabel,
  highlighted = false,
  proposal,
}: Omit<BundleProposalSummaryCardProps, "onClick">): ReactElement {
  const hasLongNotes = (proposal.notes?.length ?? 0) > LONG_NOTES_THRESHOLD;

  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-900">{proposal.title}</h3>
          <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-gray-600">
            {proposal.items.length} {proposal.items.length === 1 ? "item" : "items"}
          </span>
          {highlighted ? (
            <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[11px] font-medium text-white">
              Selected
            </span>
          ) : null}
        </div>
        {proposal.notes ? (
          <div>
            <div className={noteContainerClassName(hasLongNotes)} data-testid="bundle-summary-notes">
              {proposal.notes}
            </div>
            {hasLongNotes ? (
              <p className="mt-1 text-[11px] text-gray-500">Scroll to read the full explanation.</p>
            ) : null}
          </div>
        ) : null}
        {proposal.budget_cap_eur !== null ? (
          <p className="mt-2 text-[11px] text-gray-500">
            Budget cap: {formatBundlePrice(proposal.budget_cap_eur)}
          </p>
        ) : null}
      </div>
      <div className="shrink-0 text-right">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-gray-500">Total</p>
        <p className="text-sm font-semibold text-gray-900">{formatBundlePrice(proposal.bundle_total_eur)}</p>
        <p className="mt-1 text-[11px] text-gray-500">{formatBundleCreatedAt(proposal.created_at)}</p>
        <p className="mt-2 text-xs font-medium text-slate-700">{actionLabel}</p>
      </div>
    </div>
  );
}

export function BundleProposalSummaryCard({
  actionLabel,
  highlighted = false,
  onClick,
  proposal,
}: BundleProposalSummaryCardProps): ReactElement {
  const cardId = bundleSummaryCardId(proposal.bundle_id);
  const className = [
    "group w-full rounded-lg border p-4 text-left transition-colors",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400",
    highlighted ? "border-slate-900 bg-slate-50 ring-1 ring-slate-200" : "border-gray-200 bg-gray-50/60",
  ].join(" ");

  if (!onClick) {
    return (
      <div className={className} id={cardId}>
        <SummaryCardContent actionLabel={actionLabel} highlighted={highlighted} proposal={proposal} />
      </div>
    );
  }

  return (
    <button
      aria-controls={`${cardId}-details`}
      className={`${className} cursor-pointer hover:border-slate-300 hover:bg-gray-100 hover:shadow-sm`}
      id={cardId}
      onClick={onClick}
      type="button"
    >
      <SummaryCardContent actionLabel={actionLabel} highlighted={highlighted} proposal={proposal} />
    </button>
  );
}
