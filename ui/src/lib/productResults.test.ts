import { parseProductResults } from "./productResults";

describe("parseProductResults", () => {
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
