"use client";

import { useState, type ReactElement } from "react";

import type { BundleProposal } from "@/lib/bundleProposalsStore";

type SearchBundlePanelProps = {
  error?: string | null;
  isLoading?: boolean;
  proposals: BundleProposal[];
};

function formatPrice(value: number | null): string {
  return value === null ? "—" : `€${value.toFixed(2)}`;
}

function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleString();
}

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

export function SearchBundlePanel({
  error = null,
  isLoading = false,
  proposals,
}: SearchBundlePanelProps): ReactElement {
  const [expandedBundleIds, setExpandedBundleIds] = useState<Set<string>>(() => new Set());

  function toggleBundle(bundleId: string): void {
    setExpandedBundleIds((current) => {
      const next = new Set(current);
      if (next.has(bundleId)) {
        next.delete(bundleId);
      } else {
        next.add(bundleId);
      }
      return next;
    });
  }

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
              <button
                aria-expanded={isExpanded}
                className="flex w-full items-start justify-between gap-4 p-4 text-left"
                onClick={() => {
                  toggleBundle(proposal.bundle_id);
                }}
                type="button"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold text-gray-900">{proposal.title}</h3>
                    <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-gray-600">
                      {proposal.items.length} {proposal.items.length === 1 ? "item" : "items"}
                    </span>
                  </div>
                  {proposal.notes ? (
                    <p className="mt-1 line-clamp-2 text-xs text-gray-600">{proposal.notes}</p>
                  ) : null}
                  {proposal.budget_cap_eur !== null ? (
                    <p className="mt-1 text-[11px] text-gray-500">
                      Budget cap: {formatPrice(proposal.budget_cap_eur)}
                    </p>
                  ) : null}
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-gray-500">Total</p>
                  <p className="text-sm font-semibold text-gray-900">{formatPrice(proposal.bundle_total_eur)}</p>
                  <p className="mt-1 text-[11px] text-gray-500">{formatCreatedAt(proposal.created_at)}</p>
                  <p className="mt-2 text-xs font-medium text-gray-700">{isExpanded ? "Hide details" : "Show details"}</p>
                </div>
              </button>
              {isExpanded ? (
                <div className="border-t border-gray-200 bg-white p-4">
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
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <h4 className="text-sm font-semibold text-gray-900">{item.product_name}</h4>
                            <p className="text-[11px] text-gray-500">{item.item_id}</p>
                          </div>
                          <div className="shrink-0 text-right text-xs text-gray-600">
                            <p>Qty {item.quantity}</p>
                            <p className="font-medium text-gray-900">
                              {item.line_total_eur === null
                                ? "Pending price"
                                : formatPrice(item.line_total_eur)}
                            </p>
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
                        <p className="mt-3 text-xs text-gray-600">
                          Unit price:{" "}
                          {item.price_eur === null ? (
                            <span className="font-medium text-amber-700">Pending price</span>
                          ) : (
                            <span className="font-medium text-gray-900">{formatPrice(item.price_eur)}</span>
                          )}
                        </p>
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
