import { parseProductResults } from "./productResults";

describe("parseProductResults", () => {
  it("parses run_search_graph results payload", () => {
    const parsed = parseProductResults({
      results: [{ product_id: "prod-1", product_name: "BRIMNES Wardrobe" }],
      total_candidates: 3,
      returned_count: 1,
      warning: null,
    });
    expect(parsed).toEqual([{ id: "prod-1", name: "BRIMNES Wardrobe" }]);
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
    expect(parsed).toEqual([{ id: "prod-1", name: "BRIMNES Wardrobe" }]);
  });

  it("parses short retrieval result arrays", () => {
    const parsed = parseProductResults([
      {
        product_id: "90606797-DE",
        description_text: "Beige cylindrical planter",
      },
    ]);
    expect(parsed).toEqual([
      { id: "90606797-DE", name: "Beige cylindrical planter" },
    ]);
  });

  it("parses JSON-encoded result strings", () => {
    const parsed = parseProductResults(
      '[{"product_id":"1-DE","description_text":"Low-light plant"}]',
    );
    expect(parsed).toEqual([{ id: "1-DE", name: "Low-light plant" }]);
  });
});
