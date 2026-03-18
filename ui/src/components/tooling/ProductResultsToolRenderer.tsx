"use client";

import { useState, type ReactElement } from "react";

import { ProductImageThumbnail } from "@/components/catalog/ProductImageThumbnail";
import { formatBundlePrice } from "@/components/search/BundleProposalSummaryCard";
import type { SearchResultGroup } from "@/lib/productResults";

type QueryDisplayMetadata = {
  queryId: string;
  title: string;
  queryText: string;
};

type ProductResultsToolRendererProps = {
  groups: SearchResultGroup[];
  queryMetadata?: QueryDisplayMetadata[] | undefined;
};

function humanizeQueryId(queryId: string, index: number): string {
  if (queryId === "results") {
    return "Results";
  }
  if (/^query-\d+$/u.test(queryId)) {
    return `Query ${index + 1}`;
  }
  const humanized = queryId.replace(/[_-]+/gu, " ").trim();
  if (humanized.length === 0) {
    return `Query ${index + 1}`;
  }
  return humanized.replace(/\b\p{L}/gu, (match) => match.toUpperCase());
}

function normalizeDisplayText(value: string | null | undefined): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function ProductResultsToolRenderer({
  groups,
  queryMetadata,
}: ProductResultsToolRendererProps): ReactElement {
  const [collapsedQueryIds, setCollapsedQueryIds] = useState<Set<string>>(() => new Set());

  if (groups.length === 0) {
    return <p>No products found. Try broadening the search query.</p>;
  }

  const metadataByQueryId = new Map(
    (queryMetadata ?? []).map((metadata) => [metadata.queryId, metadata] as const),
  );

  return (
    <div className="space-y-4" data-testid="product-results">
      {groups.map((group, index) => {
        const metadata = metadataByQueryId.get(group.queryId);
        const title =
          normalizeDisplayText(metadata?.title) ?? humanizeQueryId(group.queryId, index);
        const queryText =
          normalizeDisplayText(metadata?.queryText) ??
          normalizeDisplayText(group.semanticQuery) ??
          title;
        const isCollapsed = collapsedQueryIds.has(group.queryId);
        const contentId = `product-results-${group.queryId}`;

        return (
          <section className="overflow-hidden rounded-lg border border-gray-200 bg-white" key={group.queryId}>
            <button
              aria-controls={contentId}
              aria-expanded={!isCollapsed}
              className="flex w-full items-start justify-between gap-4 bg-gray-50 px-4 py-3 text-left transition-colors hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-300"
              onClick={() => {
                setCollapsedQueryIds((current) => {
                  const next = new Set(current);
                  if (next.has(group.queryId)) {
                    next.delete(group.queryId);
                  } else {
                    next.add(group.queryId);
                  }
                  return next;
                });
              }}
              type="button"
            >
              <div className="min-w-0">
                <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-gray-500">
                  {title}
                </p>
                <h3 className="mt-1 text-sm font-semibold text-gray-900">{queryText}</h3>
                <p className="mt-1 text-xs text-gray-500">
                  {group.products.length} result{group.products.length === 1 ? "" : "s"}
                </p>
              </div>
              <span className="shrink-0 text-xs font-medium text-gray-500">
                {isCollapsed ? "Expand" : "Collapse"}
              </span>
            </button>
            {!isCollapsed ? (
              <div
                className="max-h-96 space-y-3 overflow-y-auto border-t border-gray-200 p-3"
                data-testid={`product-results-panel-${group.queryId}`}
                id={contentId}
              >
                {group.products.length === 0 ? (
                  <p className="text-sm text-gray-600">
                    No products found. Try broadening the search query.
                  </p>
                ) : (
                  group.products.map((product) => (
                    <article
                      className="rounded-lg border border-gray-200 bg-gray-50 p-3"
                      key={`${group.queryId}-${product.id}`}
                    >
                      <div className="flex gap-3">
                        <ProductImageThumbnail
                          images={product.imageUrls}
                          productName={product.name}
                          testIdPrefix={`search-result-${group.queryId}-${product.id}`}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <h4 className="text-sm font-semibold text-gray-900">{product.name}</h4>
                              <p className="text-[11px] text-gray-500">{product.id}</p>
                            </div>
                            <div className="shrink-0 rounded-md border border-gray-200 bg-white px-3 py-2">
                              <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-gray-500">
                                Price
                              </p>
                              <p className="mt-1 text-sm font-medium text-gray-900">
                                {product.priceEur === null
                                  ? "Pending"
                                  : formatBundlePrice(product.priceEur)}
                              </p>
                            </div>
                          </div>
                          <div className="mt-3">
                            <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-gray-500">
                              Description
                            </p>
                            <p className="mt-1 text-sm text-gray-600">
                              {product.descriptionText ?? "—"}
                            </p>
                          </div>
                        </div>
                      </div>
                    </article>
                  ))
                )}
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}

export type { ProductResultsToolRendererProps, QueryDisplayMetadata };
