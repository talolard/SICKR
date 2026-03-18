import { parseProductResults, parseSearchResultGroups } from "./productResults";

describe("parseProductResults", () => {
  it("parses run_search_graph results payload", () => {
    const parsed = parseProductResults({
      results: [
        {
          product_id: "prod-1",
          product_name: "BRIMNES Wardrobe",
          image_urls: ["/static/product-images/prod-1"],
        },
      ],
      total_candidates: 3,
      returned_count: 1,
      warning: null,
    });
    expect(parsed).toEqual([
      {
        id: "prod-1",
        name: "BRIMNES Wardrobe",
        descriptionText: null,
        priceEur: null,
        imageUrls: ["/static/product-images/prod-1"],
      },
    ]);
  });

  it("parses batched run_search_graph result payloads", () => {
    const parsed = parseProductResults({
      queries: [
        {
          query_id: "storage",
          semantic_query: "narrow wardrobe",
          results: [{ product_id: "prod-1", product_name: "BRIMNES Wardrobe" }],
        },
        {
          query_id: "lighting",
          semantic_query: "bedside lamp",
          results: [{ product_id: "prod-2", product_name: "HEKTAR Lamp" }],
        },
      ],
    });
    expect(parsed).toEqual([
      {
        id: "prod-1",
        name: "BRIMNES Wardrobe",
        descriptionText: null,
        priceEur: null,
        imageUrls: [],
      },
      {
        id: "prod-2",
        name: "HEKTAR Lamp",
        descriptionText: null,
        priceEur: null,
        imageUrls: [],
      },
    ]);
  });

  it("parses empty run_search_graph result payloads", () => {
    const parsed = parseProductResults({
      results: [],
      total_candidates: 0,
      returned_count: 0,
      warning: null,
    });
    expect(parsed).toEqual([]);
  });

  it("parses legacy products payload", () => {
    const parsed = parseProductResults({
      products: [{ id: "prod-1", name: "BRIMNES Wardrobe" }],
    });
    expect(parsed).toEqual([
      {
        id: "prod-1",
        name: "BRIMNES Wardrobe",
        descriptionText: null,
        priceEur: null,
        imageUrls: [],
      },
    ]);
  });

  it("parses short retrieval result arrays", () => {
    const parsed = parseProductResults([
      {
        product_id: "90606797-DE",
        description_text: "Beige cylindrical planter",
      },
    ]);
    expect(parsed).toEqual([
      {
        id: "90606797-DE",
        name: "Beige cylindrical planter",
        descriptionText: "Beige cylindrical planter",
        priceEur: null,
        imageUrls: [],
      },
    ]);
  });

  it("parses JSON-encoded result strings", () => {
    const parsed = parseProductResults(
      '[{"product_id":"1-DE","description_text":"Low-light plant"}]',
    );
    expect(parsed).toEqual([
      {
        id: "1-DE",
        name: "Low-light plant",
        descriptionText: "Low-light plant",
        priceEur: null,
        imageUrls: [],
      },
    ]);
  });

  it("parses grouped search results with image URLs", () => {
    const parsed = parseSearchResultGroups({
      queries: [
        {
          query_id: "storage",
          semantic_query: "narrow wardrobe",
          results: [
            {
              product_id: "123-DE",
              product_name: "Wardrobe",
              description_text: "Tall and narrow",
              price_eur: 99.99,
              image_urls: ["/static/product-images/123"],
            },
          ],
        },
      ],
    });

    expect(parsed).toEqual([
      {
        queryId: "storage",
        semanticQuery: "narrow wardrobe",
        products: [
          {
            id: "123-DE",
            name: "Wardrobe",
            descriptionText: "Tall and narrow",
            priceEur: 99.99,
            imageUrls: ["/static/product-images/123"],
          },
        ],
      },
    ]);
  });

  it("prefers display_title when the runtime emits enriched catalog metadata", () => {
    const parsed = parseProductResults([
      {
        product_id: "30582542-DE",
        product_name: "FEJKA",
        display_title: "FEJKA Kuenstliche Topfpflanze Drinnen Draussen Monstera",
      },
    ]);

    expect(parsed).toEqual([
      {
        id: "30582542-DE",
        name: "FEJKA Kuenstliche Topfpflanze Drinnen Draussen Monstera",
        descriptionText: null,
        priceEur: null,
        imageUrls: [],
      },
    ]);
  });
});
