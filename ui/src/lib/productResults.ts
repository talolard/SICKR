export type Product = {
  id: string;
  name: string;
  descriptionText: string | null;
  priceEur: number | null;
  imageUrls: string[];
};

export type SearchResultGroup = {
  queryId: string;
  semanticQuery: string;
  products: Product[];
};

type ProductLike = {
  id?: unknown;
  name?: unknown;
  product_id?: unknown;
  product_name?: unknown;
  description_text?: unknown;
  price_eur?: unknown;
  image_urls?: unknown;
};

type QueryLike = {
  query_id?: unknown;
  semantic_query?: unknown;
  results?: unknown;
};

function parseProduct(item: unknown): Product | null {
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
  const imageUrls = Array.isArray(candidate.image_urls)
    ? candidate.image_urls.filter((value): value is string => typeof value === "string")
    : [];
  return {
    id,
    name: typeof nameCandidate === "string" ? nameCandidate : id,
    descriptionText:
      typeof candidate.description_text === "string" ? candidate.description_text : null,
    priceEur: typeof candidate.price_eur === "number" ? candidate.price_eur : null,
    imageUrls,
  };
}

function parseFromArray(items: unknown[]): Product[] {
  return items
    .map((item): Product | null => parseProduct(item))
    .filter((item): item is Product => item !== null);
}

function singleGroup(products: Product[]): SearchResultGroup[] {
  return [{ queryId: "results", semanticQuery: "Results", products }];
}

export function parseSearchResultGroups(result: unknown): SearchResultGroup[] | null {
  if (typeof result === "string") {
    try {
      return parseSearchResultGroups(JSON.parse(result) as unknown);
    } catch {
      return null;
    }
  }
  if (Array.isArray(result)) {
    return singleGroup(parseFromArray(result));
  }
  if (typeof result !== "object" || result === null) {
    return null;
  }
  if ("products" in result) {
    const products = (result as { products: unknown }).products;
    if (!Array.isArray(products)) {
      return null;
    }
    return singleGroup(parseFromArray(products));
  }
  if ("results" in result) {
    const products = (result as { results: unknown }).results;
    if (!Array.isArray(products)) {
      return null;
    }
    return singleGroup(parseFromArray(products));
  }
  if (!("queries" in result)) {
    return null;
  }
  const queries = (result as { queries: unknown }).queries;
  if (!Array.isArray(queries)) {
    return null;
  }
  return queries.map((query, index): SearchResultGroup => {
    const candidate = (typeof query === "object" && query !== null ? query : {}) as QueryLike;
    return {
      queryId:
        typeof candidate.query_id === "string" ? candidate.query_id : `query-${index + 1}`,
      semanticQuery:
        typeof candidate.semantic_query === "string"
          ? candidate.semantic_query
          : `Query ${index + 1}`,
      products: Array.isArray(candidate.results) ? parseFromArray(candidate.results) : [],
    };
  });
}

export function parseProductResults(result: unknown): Product[] | null {
  const groups = parseSearchResultGroups(result);
  if (!groups) {
    return null;
  }
  return groups.flatMap((group) => group.products);
}
