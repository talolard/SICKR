"use client";

import { useEffect, useMemo, useState, type ReactElement } from "react";

import type { BundleProposal } from "@/lib/bundleProposalsStore";
import {
  bundleSummaryCardId,
  BundleProposalSummaryCard,
  formatBundlePrice,
} from "@/components/search/BundleProposalSummaryCard";
import { ProductImageThumbnail } from "@/components/catalog/ProductImageThumbnail";

function validationTone(status: BundleProposal["validations"][number]["status"]): string {
  switch (status) {
    case "pass":
      return "bg-green-100 text-green-800";
    case "fail":
      return "bg-red-100 text-red-800";
    case "warn":
      return "bg-amber-100 text-amber-800";
    case "unknown":
      return "bg-slate-100 text-slate-700";
  }
}

function validationLabel(kind: BundleProposal["validations"][number]["kind"]): string {
  switch (kind) {
    case "budget_max_eur":
      return "Budget";
    case "pricing_complete":
      return "Pricing";
    case "duplicate_items":
      return "Duplicates";
  }
}

function bundleItemDisplayName(item: BundleProposal["items"][number]): string {
  return item.display_title ?? item.product_name;
}

function BundleValidationList({ proposal }: { proposal: BundleProposal }): ReactElement | null {
  if (proposal.validations.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {proposal.validations.map((validation) => (
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-medium ${validationTone(validation.status)}`}
          key={`${proposal.bundle_id}-${validation.kind}-${validation.message}`}
        >
          <span className="font-medium">{validationLabel(validation.kind)}:</span> {validation.message}
        </span>
      ))}
    </div>
  );
}

type SearchBundlePanelProps = {
  activeBundleId?: string | null;
  error?: string | null;
  isLoading?: boolean;
  proposals: BundleProposal[];
};

export function SearchBundlePanel({
  activeBundleId = null,
  error = null,
  isLoading = false,
  proposals,
}: SearchBundlePanelProps): ReactElement {
  const [manuallyExpandedBundleIds, setManuallyExpandedBundleIds] = useState<Set<string>>(
    () => new Set(),
  );

  const expandedBundleIds = useMemo(() => {
    if (!activeBundleId) {
      return manuallyExpandedBundleIds;
    }
    const next = new Set(manuallyExpandedBundleIds);
    next.add(activeBundleId);
    return next;
  }, [activeBundleId, manuallyExpandedBundleIds]);

  function toggleBundle(bundleId: string): void {
    setManuallyExpandedBundleIds((current) => {
      const next = new Set(current);
      if (next.has(bundleId)) {
        next.delete(bundleId);
      } else {
        next.add(bundleId);
      }
      return next;
    });
  }

  useEffect(() => {
    if (!activeBundleId) {
      return;
    }
    globalThis.window?.requestAnimationFrame(() => {
      document.getElementById(bundleSummaryCardId(activeBundleId))?.scrollIntoView?.({
        behavior: "smooth",
        block: "nearest",
      });
    });
  }, [activeBundleId]);

  if (proposals.length === 0) {
    return (
      <section
        className="flex h-full min-h-0 flex-col rounded-[24px] border border-slate-200 bg-white/92 p-4 shadow-[0_14px_40px_-36px_rgba(15,23,42,0.45)]"
        data-testid="search-bundle-panel-root"
      >
        <h2 className="text-lg font-semibold tracking-tight text-slate-950">Bundles</h2>
        {isLoading ? <p className="mt-2 text-sm text-slate-500">Loading saved bundle proposals...</p> : null}
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Proposed bundles will appear here when the search agent assembles one.
        </p>
      </section>
    );
  }

  return (
    <section
      className="flex h-full min-h-0 flex-col rounded-[24px] border border-slate-200 bg-white/92 p-4 shadow-[0_14px_40px_-36px_rgba(15,23,42,0.45)]"
      data-testid="search-bundle-panel-root"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            Search bundles
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">Bundles</h2>
          <p className="text-sm leading-6 text-slate-600">
            Summaries stay compact until you open the items and validation details.
          </p>
        </div>
        {isLoading ? <p className="text-xs text-slate-500">Syncing saved bundles...</p> : null}
      </div>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-4 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {proposals.map((proposal) => {
          const isExpanded = expandedBundleIds.has(proposal.bundle_id);

          return (
            <article
              className="overflow-hidden rounded-[24px] border border-slate-200 bg-[linear-gradient(180deg,rgba(248,250,252,0.82),rgba(255,255,255,0.98))]"
              key={proposal.bundle_id}
            >
              <BundleProposalSummaryCard
                actionLabel={isExpanded ? "Hide details" : "Show details"}
                expanded={isExpanded}
                highlighted={proposal.bundle_id === activeBundleId}
                onClick={() => {
                  toggleBundle(proposal.bundle_id);
                }}
                proposal={proposal}
              />
              {isExpanded ? (
                <div
                  className="border-t border-slate-200 bg-white/95 p-4"
                  id={`${bundleSummaryCardId(proposal.bundle_id)}-details`}
                >
                  <BundleValidationList proposal={proposal} />
                  <div className="mt-4 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">Included items</p>
                      <p className="text-xs text-slate-500">
                        Compare quantities, total cost, and rationale at a glance.
                      </p>
                    </div>
                  </div>
                  <div
                    className="mt-3 max-h-[32rem] space-y-3 overflow-y-auto pr-1"
                    data-testid={`bundle-items-${proposal.bundle_id}`}
                  >
                    {proposal.items.map((item) => (
                      <article
                        className="rounded-[22px] border border-slate-200 bg-slate-50/70 p-3"
                        key={`${proposal.bundle_id}-${item.item_id}`}
                      >
                        <div className="flex gap-3">
                          <ProductImageThumbnail
                            images={item.image_urls}
                            productName={bundleItemDisplayName(item)}
                            testIdPrefix={`bundle-item-${proposal.bundle_id}-${item.item_id}`}
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                                  Bundle item
                                </p>
                                <h4 className="mt-1 text-sm font-semibold text-slate-900">
                                  {bundleItemDisplayName(item)}
                                </h4>
                                <p className="text-[11px] text-slate-500">{item.item_id}</p>
                                {item.product_url ? (
                                  <a
                                    aria-label={`Open product page for ${bundleItemDisplayName(item)}`}
                                    className="mt-1 inline-flex text-xs font-medium text-pink-700 underline underline-offset-2 hover:text-pink-800"
                                    href={item.product_url}
                                    rel="noreferrer"
                                    target="_blank"
                                  >
                                    Open product page
                                  </a>
                                ) : null}
                              </div>
                              <div className="shrink-0 rounded-2xl border border-slate-200 bg-white px-3 py-2">
                                <dl className="grid grid-cols-3 gap-3 text-left text-xs text-gray-600">
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-slate-500">Unit</dt>
                                    <dd className="mt-1 font-medium text-slate-900">
                                      {item.price_eur === null
                                        ? "Pending"
                                        : formatBundlePrice(item.price_eur)}
                                    </dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-slate-500">Qty</dt>
                                    <dd className="mt-1 font-medium text-slate-900">{item.quantity}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-slate-500">Total</dt>
                                    <dd className="mt-1 font-medium text-slate-900">
                                      {item.line_total_eur === null
                                        ? "Pending"
                                        : formatBundlePrice(item.line_total_eur)}
                                    </dd>
                                  </div>
                                </dl>
                              </div>
                            </div>
                            <dl className="mt-3 grid gap-3 md:grid-cols-2">
                              <div>
                                <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500">
                                  Why it is in the bundle
                                </dt>
                                <dd className="mt-1 text-sm leading-6 text-slate-700">{item.reason}</dd>
                              </div>
                              <div>
                                <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-slate-500">
                                  Description
                                </dt>
                                <dd className="mt-1 text-sm leading-6 text-slate-600">
                                  {item.description_text ?? "—"}
                                </dd>
                              </div>
                            </dl>
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
