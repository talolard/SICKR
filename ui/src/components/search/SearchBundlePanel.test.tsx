import { render, screen } from "@testing-library/react";

import { SearchBundlePanel } from "./SearchBundlePanel";

describe("SearchBundlePanel", () => {
  it("renders empty state when there are no proposals", () => {
    render(<SearchBundlePanel proposals={[]} />);

    expect(screen.getByText("Bundles")).toBeInTheDocument();
    expect(screen.getByText(/will appear here/i)).toBeInTheDocument();
  });

  it("renders bundle proposals with totals and reasons", () => {
    render(
      <SearchBundlePanel
        proposals={[
          {
            bundle_id: "bundle-1",
            title: "Desk setup",
            notes: "Balanced for reading and writing.",
            budget_cap_eur: 200,
            items: [
              {
                item_id: "chair-1",
                product_name: "Chair One",
                description_text: "Desk chair",
                price_eur: 79.99,
                quantity: 2,
                line_total_eur: 159.98,
                reason: "Two matching chairs",
              },
            ],
            bundle_total_eur: 159.98,
            validations: [
              {
                kind: "budget_max_eur",
                status: "pass",
                message: "Bundle total €159.98 is within budget cap €200.00.",
              },
            ],
            created_at: "2026-03-11T11:00:00Z",
            run_id: "run-1",
          },
        ]}
      />,
    );

    expect(screen.getByText("Desk setup")).toBeInTheDocument();
    expect(screen.getByText("Balanced for reading and writing.")).toBeInTheDocument();
    expect(screen.getByText("Chair One")).toBeInTheDocument();
    expect(screen.getByText("Two matching chairs")).toBeInTheDocument();
    expect(screen.getByText("Total: €159.98")).toBeInTheDocument();
  });
});
