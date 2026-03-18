import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProductResultsToolRenderer } from "./ProductResultsToolRenderer";

describe("ProductResultsToolRenderer", () => {
  it("renders grouped product cards for non-empty results", () => {
    render(
      <ProductResultsToolRenderer
        groups={[
          {
            queryId: "storage",
            semanticQuery: "narrow wardrobe",
            products: [
              {
                id: "prod-001",
                name: "BRIMNES Wardrobe",
                descriptionText: "Tall wardrobe",
                priceEur: 99.99,
                imageUrls: ["/static/product-images/prod-001"],
              },
              {
                id: "prod-002",
                name: "PAX Shelf",
                descriptionText: null,
                priceEur: null,
                imageUrls: [],
              },
            ],
          },
        ]}
        queryMetadata={[
          {
            queryId: "storage",
            title: "Storage options",
            queryText: "narrow wardrobe",
          },
        ]}
      />,
    );

    expect(screen.getByTestId("product-results")).toBeInTheDocument();
    expect(screen.getByText("Storage options")).toBeInTheDocument();
    expect(screen.getByText("narrow wardrobe")).toBeInTheDocument();
    expect(screen.getByText("2 results")).toBeInTheDocument();
    expect(screen.getByText("BRIMNES Wardrobe")).toBeInTheDocument();
    expect(screen.getByText("PAX Shelf")).toBeInTheDocument();
    expect(screen.getByTestId("product-results-panel-storage")).toHaveClass(
      "max-h-96",
      "overflow-y-auto",
    );
    expect(
      screen.getByTestId("search-result-storage-prod-002-placeholder"),
    ).toBeInTheDocument();
  });

  it("collapses and re-expands a query section while keeping the summary visible", async () => {
    const user = userEvent.setup();

    render(
      <ProductResultsToolRenderer
        groups={[
          {
            queryId: "storage",
            semanticQuery: "narrow wardrobe",
            products: [
              {
                id: "prod-001",
                name: "BRIMNES Wardrobe",
                descriptionText: "Tall wardrobe",
                priceEur: 99.99,
                imageUrls: [],
              },
            ],
          },
        ]}
        queryMetadata={[
          {
            queryId: "storage",
            title: "Storage options",
            queryText: "narrow wardrobe",
          },
        ]}
      />,
    );

    const toggle = screen.getByRole("button", { name: /Storage options/i });

    await user.click(toggle);

    expect(screen.getByText("Storage options")).toBeInTheDocument();
    expect(screen.getByText("narrow wardrobe")).toBeInTheDocument();
    expect(screen.getByText("1 result")).toBeInTheDocument();
    expect(screen.queryByText("BRIMNES Wardrobe")).not.toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);

    expect(screen.getByText("BRIMNES Wardrobe")).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("opens the gallery popover for products with multiple images", async () => {
    const user = userEvent.setup();

    render(
      <ProductResultsToolRenderer
        groups={[
          {
            queryId: "lighting",
            semanticQuery: "task lamp",
            products: [
              {
                id: "prod-003",
                name: "HEKTAR Lamp",
                descriptionText: "Adjustable lamp",
                priceEur: 59.99,
                imageUrls: [
                  "/static/product-images/prod-003",
                  "/static/product-images/prod-003/2",
                ],
              },
            ],
          },
        ]}
      />,
    );

    await user.click(screen.getByTestId("search-result-lighting-prod-003-button"));

    expect(
      screen.getByTestId("search-result-lighting-prod-003-popover"),
    ).toBeInTheDocument();
    expect(screen.getByText("Image 1 of 2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Image 2 of 2")).toBeInTheDocument();
  });

  it("renders per-query empty-state guidance", () => {
    render(
      <ProductResultsToolRenderer
        groups={[{ queryId: "empty", semanticQuery: "nothing", products: [] }]}
        queryMetadata={[{ queryId: "empty", title: "Empty search", queryText: "nothing" }]}
      />,
    );

    expect(screen.getByText("Empty search")).toBeInTheDocument();
    expect(screen.getByText("0 results")).toBeInTheDocument();
    expect(
      screen.getByText("No products found. Try broadening the search query."),
    ).toBeInTheDocument();
  });
});
