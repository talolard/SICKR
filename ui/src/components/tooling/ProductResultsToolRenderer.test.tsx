import { render, screen } from "@testing-library/react";

import { ProductResultsToolRenderer } from "./ProductResultsToolRenderer";

describe("ProductResultsToolRenderer", () => {
  it("renders product cards for non-empty results", () => {
    render(
      <ProductResultsToolRenderer
        products={[
          { id: "prod-001", name: "BRIMNES Wardrobe" },
          { id: "prod-002", name: "PAX Shelf" },
        ]}
      />,
    );

    expect(screen.getByTestId("product-results")).toBeInTheDocument();
    expect(screen.getByText("BRIMNES Wardrobe")).toBeInTheDocument();
    expect(screen.getByText("PAX Shelf")).toBeInTheDocument();
  });

  it("renders no-results guidance for empty results", () => {
    render(<ProductResultsToolRenderer products={[]} />);

    expect(
      screen.getByText("No products found. Try broadening the search query."),
    ).toBeInTheDocument();
  });
});
