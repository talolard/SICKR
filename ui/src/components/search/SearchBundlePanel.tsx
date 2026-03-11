"use client";

import type { ReactElement } from "react";

import type { BundleProposal } from "@/lib/bundleProposalsStore";

type SearchBundlePanelProps = {
  error?: string | null;
  isLoading?: boolean;
  proposals: BundleProposal[];
};

function formatPrice(value: number | null): string {
  return value === null ? "—" : `€${value.toFixed(2)}`;
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

export function SearchBundlePanel({
  error = null,
  isLoading = false,
  proposals,
}: SearchBundlePanelProps): ReactElement {
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
        <h2 className="text-lg font-semibold text-gray-900">Bundles</h2>
        {isLoading ? <p className="text-xs text-gray-500">Syncing saved bundles…</p> : null}
      </div>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-3 space-y-4">
        {proposals.map((proposal) => (
          <article className="rounded border border-gray-200 p-3" key={proposal.bundle_id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{proposal.title}</h3>
                {proposal.notes ? <p className="mt-1 text-xs text-gray-600">{proposal.notes}</p> : null}
                {proposal.budget_cap_eur !== null ? (
                  <p className="mt-1 text-[11px] text-gray-500">
                    Budget cap: {formatPrice(proposal.budget_cap_eur)}
                  </p>
                ) : null}
              </div>
              <p className="text-xs text-gray-500">{new Date(proposal.created_at).toLocaleString()}</p>
            </div>
            {proposal.validations.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-2">
                {proposal.validations.map((validation) => (
                  <span
                    className={`rounded px-2 py-1 text-xs ${validationTone(validation.status)}`}
                    key={`${proposal.bundle_id}-${validation.kind}-${validation.message}`}
                  >
                    <span className="font-medium">{validationLabel(validation.kind)}:</span> {validation.message}
                  </span>
                ))}
              </div>
            ) : null}
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="text-gray-500">
                  <tr>
                    <th className="pb-2 pr-3">Item</th>
                    <th className="pb-2 pr-3">Price</th>
                    <th className="pb-2 pr-3">Qty</th>
                    <th className="pb-2 pr-3">Line total</th>
                    <th className="pb-2 pr-3">Description</th>
                    <th className="pb-2">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {proposal.items.map((item) => (
                    <tr className="align-top" key={`${proposal.bundle_id}-${item.item_id}`}>
                      <td className="py-2 pr-3 font-medium text-gray-900">
                        {item.product_name}
                        <p className="text-[11px] text-gray-500">{item.item_id}</p>
                      </td>
                      <td className="py-2 pr-3">
                        {item.price_eur === null ? (
                          <span className="text-amber-700">Pending price</span>
                        ) : (
                          formatPrice(item.price_eur)
                        )}
                      </td>
                      <td className="py-2 pr-3">{item.quantity}</td>
                      <td className="py-2 pr-3">
                        {item.line_total_eur === null ? (
                          <span className="text-amber-700">Pending price</span>
                        ) : (
                          formatPrice(item.line_total_eur)
                        )}
                      </td>
                      <td className="py-2 pr-3 text-gray-600">{item.description_text ?? "—"}</td>
                      <td className="py-2 text-gray-700">{item.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex justify-end border-t pt-2 text-sm font-semibold text-gray-900">
              Total: {formatPrice(proposal.bundle_total_eur)}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
