import type { ReactElement } from "react";

type ProductResult = {
  id: string;
  name: string;
};

type ProductResultsToolRendererProps = {
  products: ProductResult[];
};

export function ProductResultsToolRenderer(
  props: ProductResultsToolRendererProps,
): ReactElement {
  const { products } = props;

  if (products.length === 0) {
    return <p>No products found. Try broadening the search query.</p>;
  }

  return (
    <ul className="space-y-2" data-testid="product-results">
      {products.map((product) => (
        <li className="rounded border p-2" key={product.id}>
          <p className="font-medium">{product.name}</p>
          <p className="text-xs text-gray-600">ID: {product.id}</p>
        </li>
      ))}
    </ul>
  );
}

export type { ProductResult, ProductResultsToolRendererProps };
