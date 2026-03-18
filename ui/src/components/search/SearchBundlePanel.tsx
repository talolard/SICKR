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
    <div className="mt-3 flex flex-wrap gap-2">
      {proposal.validations.map((validation) => (
        <span
          className={`rounded px-2 py-1 text-xs ${validationTone(validation.status)}`}
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
      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-lg font-semibold text-gray-900">Bundles</h2>
        {isLoading ? <p className="mt-2 text-sm text-gray-500">Loading saved bundle proposals...</p> : null}
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        <p className="mt-2 text-sm text-gray-600">
          Proposed bundles will appear here when the search agent assembles one.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Bundles</h2>
          <p className="text-sm text-gray-600">Collapsed by default so the workbench stays readable.</p>
        </div>
        {isLoading ? <p className="text-xs text-gray-500">Syncing saved bundles…</p> : null}
      </div>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-3 space-y-3">
        {proposals.map((proposal) => {
          const isExpanded = expandedBundleIds.has(proposal.bundle_id);

          return (
            <article className="rounded-lg border border-gray-200 bg-gray-50/60" key={proposal.bundle_id}>
              <BundleProposalSummaryCard
                actionLabel={isExpanded ? "Hide details" : "Show details"}
                highlighted={proposal.bundle_id === activeBundleId}
                onClick={() => {
                  toggleBundle(proposal.bundle_id);
                }}
                proposal={proposal}
              />
              {isExpanded ? (
                <div
                  className="border-t border-gray-200 bg-white p-4"
                  id={`${bundleSummaryCardId(proposal.bundle_id)}-details`}
                >
                  <BundleValidationList proposal={proposal} />
                  <div
                    className="mt-3 max-h-96 space-y-3 overflow-y-auto pr-1"
                    data-testid={`bundle-items-${proposal.bundle_id}`}
                  >
                    {proposal.items.map((item) => (
                      <article
                        className="rounded-lg border border-gray-200 bg-gray-50 p-3"
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
                                <h4 className="text-sm font-semibold text-gray-900">
                                  {bundleItemDisplayName(item)}
                                </h4>
                                <p className="text-[11px] text-gray-500">{item.item_id}</p>
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
                              <div className="shrink-0 rounded-md border border-gray-200 bg-white px-3 py-2">
                                <dl className="grid grid-cols-3 gap-3 text-left text-xs text-gray-600">
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-gray-500">Unit</dt>
                                    <dd className="mt-1 font-medium text-gray-900">
                                      {item.price_eur === null
                                        ? "Pending"
                                        : formatBundlePrice(item.price_eur)}
                                    </dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-gray-500">Qty</dt>
                                    <dd className="mt-1 font-medium text-gray-900">{item.quantity}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium uppercase tracking-[0.14em] text-gray-500">Total</dt>
                                    <dd className="mt-1 font-medium text-gray-900">
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
                                <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-gray-500">
                                  Why it is in the bundle
                                </dt>
                                <dd className="mt-1 text-sm text-gray-700">{item.reason}</dd>
                              </div>
                              <div>
                                <dt className="text-[11px] font-medium uppercase tracking-[0.14em] text-gray-500">
                                  Description
                                </dt>
                                <dd className="mt-1 text-sm text-gray-600">{item.description_text ?? "—"}</dd>
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
