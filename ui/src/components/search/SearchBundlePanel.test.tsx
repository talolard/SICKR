import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SearchBundlePanel } from "./SearchBundlePanel";

describe("SearchBundlePanel", () => {
  it("renders empty state when there are no proposals", () => {
    render(<SearchBundlePanel proposals={[]} />);

    expect(screen.getByText("Bundles")).toBeInTheDocument();
    expect(screen.getByText(/will appear here/i)).toBeInTheDocument();
  });

  it("renders collapsed bundle summaries with totals by default", () => {
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
                kind: "pricing_complete",
                status: "pass",
                message: "All bundle items have prices, so the total is complete.",
              },
            ],
            created_at: "2026-03-11T11:00:00Z",
            run_id: "run-1",
          },
        ]}
      />,
    );

    expect(screen.getByText("Desk setup")).toBeInTheDocument();
    expect(screen.getByText("€159.98")).toBeInTheDocument();
    expect(screen.getByText("1 item")).toBeInTheDocument();
    expect(screen.queryByText("Two matching chairs")).not.toBeInTheDocument();
  });

  it("reveals scrollable bundle details and rationale when expanded", async () => {
    const user = userEvent.setup();

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
                kind: "pricing_complete",
                status: "pass",
                message: "All bundle items have prices, so the total is complete.",
              },
              {
                kind: "duplicate_items",
                status: "warn",
                message: "Merged 1 repeated product entry into combined quantities.",
              },
            ],
            created_at: "2026-03-11T11:00:00Z",
            run_id: "run-1",
          },
        ]}
      />,
    );

    await user.click(screen.getByRole("button", { name: /desk setup/i }));

    expect(screen.getByText("Why it is in the bundle")).toBeInTheDocument();
    expect(screen.getByText("Two matching chairs")).toBeInTheDocument();
    expect(screen.getByText("Chair One")).toBeInTheDocument();
    expect(screen.getByText(/Pricing:/)).toBeInTheDocument();
    expect(screen.getByText(/Duplicates:/)).toBeInTheDocument();
    expect(screen.getByTestId("bundle-items-bundle-1")).toHaveClass("max-h-96", "overflow-y-auto");
  });
});
