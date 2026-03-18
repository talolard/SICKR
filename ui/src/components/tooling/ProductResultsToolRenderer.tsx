import type { ReactElement } from "react";

import { ProductImageThumbnail } from "@/components/catalog/ProductImageThumbnail";
import { formatBundlePrice } from "@/components/search/BundleProposalSummaryCard";
import type { SearchResultGroup } from "@/lib/productResults";

type ProductResultsToolRendererProps = {
  groups: SearchResultGroup[];
};

export function ProductResultsToolRenderer({
  groups,
}: ProductResultsToolRendererProps): ReactElement {
  const totalProductCount = groups.reduce((sum, group) => sum + group.products.length, 0);

  if (totalProductCount === 0) {
    return <p>No products found. Try broadening the search query.</p>;
  }

  return (
    <div className="space-y-4" data-testid="product-results">
      {groups.map((group) => (
        <section className="space-y-3" key={group.queryId}>
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="text-sm font-semibold text-gray-900">{group.semanticQuery}</h3>
            <p className="text-xs text-gray-500">
              {group.products.length} result{group.products.length === 1 ? "" : "s"}
            </p>
          </div>
          <div className="space-y-3">
            {group.products.map((product) => (
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
                          {product.priceEur === null ? "Pending" : formatBundlePrice(product.priceEur)}
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
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

export type { ProductResultsToolRendererProps };
