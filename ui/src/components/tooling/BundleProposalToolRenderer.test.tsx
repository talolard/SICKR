import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { BundleProposalToolRenderer } from "./BundleProposalToolRenderer";

describe("BundleProposalToolRenderer", () => {
  it("renders a clickable bundle summary card in chat", async () => {
    const user = userEvent.setup();
    const onOpenBundle = vi.fn();

    render(
      <BundleProposalToolRenderer
        onOpenBundle={onOpenBundle}
        proposal={{
          bundle_id: "bundle-1",
          title: "Wireless Hallway Lighting Starter Bundle",
          notes: "Portable lamps with an adhesive-friendly placement strategy.",
          budget_cap_eur: null,
          items: [
            {
              item_id: "lamp-1",
              product_name: "Portable lamp",
              description_text: "Desk lamp",
              price_eur: 17.99,
              quantity: 2,
              line_total_eur: 35.98,
              reason: "Portable light source",
              image_urls: [],
            },
          ],
          bundle_total_eur: 35.98,
          validations: [],
          created_at: "2026-03-17T10:00:00Z",
          run_id: "run-1",
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: /wireless hallway lighting starter bundle/i }));

    expect(onOpenBundle).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Open bundle details")).toBeInTheDocument();
  });

  it("renders a saved-state bundle card when the chat card is informational only", () => {
    render(
      <BundleProposalToolRenderer
        proposal={{
          bundle_id: "bundle-1",
          title: "Wireless Hallway Lighting Starter Bundle",
          notes: "Portable lamps with an adhesive-friendly placement strategy.",
          budget_cap_eur: null,
          items: [
            {
              item_id: "lamp-1",
              product_name: "Portable lamp",
              description_text: "Desk lamp",
              price_eur: 17.99,
              quantity: 2,
              line_total_eur: 35.98,
              reason: "Portable light source",
              image_urls: [],
            },
          ],
          bundle_total_eur: 35.98,
          validations: [],
          created_at: "2026-03-17T10:00:00Z",
          run_id: "run-1",
        }}
      />,
    );

    expect(screen.getByText("Saved to bundles panel")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /wireless hallway lighting starter bundle/i }),
    ).not.toBeInTheDocument();
  });
});
