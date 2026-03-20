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
  const visibleValidations = proposal.validations.filter((validation) => validation.status !== "pass");
  if (visibleValidations.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {visibleValidations.map((validation) => (
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
        className="editorial-panel-elevated flex h-full min-h-0 flex-col rounded-[30px] p-5"
        data-testid="search-bundle-panel-root"
      >
        <p className="editorial-eyebrow">Curated results</p>
        <h2 className="editorial-display mt-3 text-[1.8rem] leading-none text-primary">Bundles</h2>
        {isLoading ? (
          <p className="mt-3 text-sm text-on-surface-variant">Loading saved bundle proposals...</p>
        ) : null}
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        <p className="mt-3 text-sm leading-6 text-on-surface-variant">
          Proposed bundles will appear here when the search agent assembles one.
        </p>
      </section>
    );
  }

  return (
    <section
      className="editorial-panel-elevated flex h-full min-h-0 flex-col rounded-[30px] p-4"
      data-testid="search-bundle-panel-root"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
          {proposals.length} bundle{proposals.length === 1 ? "" : "s"}
        </p>
        {isLoading ? <p className="text-xs text-on-surface-variant">Syncing saved bundles...</p> : null}
      </div>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-3 min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {proposals.map((proposal) => {
          const isExpanded = expandedBundleIds.has(proposal.bundle_id);

          return (
            <article
              className="overflow-hidden rounded-[28px] bg-[color:var(--surface-container-low)] shadow-[var(--panel-shadow)]"
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
                  className="bg-[color:var(--surface-container-lowest)] p-4"
                  id={`${bundleSummaryCardId(proposal.bundle_id)}-details`}
                >
                  <BundleValidationList proposal={proposal} />
                  <div
                    className="mt-4 max-h-[32rem] space-y-3 overflow-y-auto pr-1"
                    data-testid={`bundle-items-${proposal.bundle_id}`}
                  >
                    {proposal.items.map((item) => (
                      <article
                        className="rounded-[24px] bg-[color:var(--surface-container-low)] p-3"
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
                                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
                                  Bundle item
                                </p>
                                <h4 className="mt-1 text-sm font-semibold text-primary">
                                  {bundleItemDisplayName(item)}
                                </h4>
                                <p className="text-[11px] text-on-surface-variant">{item.item_id}</p>
                                {item.product_url ? (
                                  <a
                                    aria-label={`Open product page for ${bundleItemDisplayName(item)}`}
                                    className="mt-1 inline-flex text-xs font-medium text-primary underline underline-offset-2"
                                    href={item.product_url}
                                    rel="noreferrer"
                                    target="_blank"
                                  >
                                    Open product page
                                  </a>
                                ) : null}
                              </div>
                              <div className="shrink-0 rounded-[20px] bg-[color:var(--surface-container-lowest)] px-3 py-2 shadow-[var(--panel-shadow)]">
                                <dl className="grid grid-cols-3 gap-3 text-left text-xs text-on-surface-variant">
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-on-surface-variant">Unit</dt>
                                    <dd className="mt-1 font-medium text-primary">
                                      {item.price_eur === null
                                        ? "Pending"
                                        : formatBundlePrice(item.price_eur)}
                                    </dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-on-surface-variant">Qty</dt>
                                    <dd className="mt-1 font-medium text-primary">{item.quantity}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-on-surface-variant">Total</dt>
                                    <dd className="mt-1 font-medium text-primary">
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
                                <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-on-surface-variant">
                                  Why it is in the bundle
                                </dt>
                                <dd className="mt-1 text-sm leading-6 text-on-surface">{item.reason}</dd>
                              </div>
                              <div>
                                <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-on-surface-variant">
                                  Description
                                </dt>
                                <dd className="mt-1 text-sm leading-6 text-on-surface-variant">
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
