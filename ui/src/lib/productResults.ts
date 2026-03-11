export type Product = {
  id: string;
  name: string;
};

type ProductLike = {
  id?: unknown;
  name?: unknown;
  product_id?: unknown;
  product_name?: unknown;
  description_text?: unknown;
};

function parseFromArray(items: unknown[]): Product[] {
  return items
    .map((item): Product | null => {
      if (typeof item !== "object" || item === null) {
        return null;
      }
      const candidate = item as ProductLike;
      const id =
        typeof candidate.id === "string"
          ? candidate.id
          : typeof candidate.product_id === "string"
            ? candidate.product_id
            : null;
      if (!id) {
        return null;
      }
      const nameCandidate =
        typeof candidate.name === "string"
          ? candidate.name
          : typeof candidate.product_name === "string"
            ? candidate.product_name
            : typeof candidate.description_text === "string"
              ? candidate.description_text
              : candidate.product_id;
      return {
        id,
        name: typeof nameCandidate === "string" ? nameCandidate : id,
      };
    })
    .filter((item): item is Product => item !== null);
}

export function parseProductResults(result: unknown): Product[] | null {
  if (typeof result === "string") {
    try {
      return parseProductResults(JSON.parse(result) as unknown);
    } catch {
      return null;
    }
  }
  if (Array.isArray(result)) {
    return parseFromArray(result);
  }
  if (typeof result === "object" && result !== null) {
    if ("products" in result) {
      const products = (result as { products: unknown }).products;
      if (!Array.isArray(products)) {
        return null;
      }
      return parseFromArray(products);
    }
    if ("results" in result) {
      const products = (result as { results: unknown }).results;
      if (!Array.isArray(products)) {
        return null;
      }
      return parseFromArray(products);
    }
    if ("queries" in result) {
      const queries = (result as { queries: unknown }).queries;
      if (!Array.isArray(queries)) {
        return null;
      }
      return queries.flatMap((query) => {
        if (typeof query !== "object" || query === null || !("results" in query)) {
          return [];
        }
        const products = (query as { results: unknown }).results;
        return Array.isArray(products) ? parseFromArray(products) : [];
      });
    }
  }
  return null;
}
