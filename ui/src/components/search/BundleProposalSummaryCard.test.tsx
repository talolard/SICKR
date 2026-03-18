import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import type { BundleProposal } from "@/lib/bundleProposalsStore";

import { BundleProposalSummaryCard } from "./BundleProposalSummaryCard";

const longNotes =
  "This bundle keeps the room usable for reading, writing, and overnight guests while staying within the " +
  "footprint you described. The extra chair can move between the desk and the dining area, and the storage " +
  "piece keeps cables and notebooks out of sight without blocking circulation.";

const proposal: BundleProposal = {
  bundle_id: "bundle-1",
  title: "Desk setup",
  notes: longNotes,
  budget_cap_eur: 240,
  items: [
    {
      item_id: "chair-1",
      product_name: "Chair One",
      description_text: "Desk chair",
      price_eur: 79.99,
      quantity: 2,
      line_total_eur: 159.98,
      reason: "Two matching chairs",
      image_urls: [],
    },
  ],
  bundle_total_eur: 159.98,
  validations: [],
  created_at: "2026-03-11T11:00:00Z",
  run_id: "run-1",
};

describe("BundleProposalSummaryCard", () => {
  it("shows a scroll affordance for long bundle notes", () => {
    render(<BundleProposalSummaryCard actionLabel="Show details" proposal={proposal} />);

    expect(screen.getByTestId("bundle-summary-notes")).toHaveClass("max-h-24", "overflow-y-auto");
    expect(screen.getByText("Scroll to read the full explanation.")).toBeInTheDocument();
  });

  it("renders clickable hoverable cards and forwards the click", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <BundleProposalSummaryCard
        actionLabel="Open bundle details"
        highlighted
        onClick={onClick}
        proposal={proposal}
      />,
    );

    const button = screen.getByRole("button", { name: /desk setup/i });
    expect(button).toHaveClass("cursor-pointer", "hover:border-slate-300", "hover:shadow-sm");
    expect(button).toHaveClass("border-slate-900");
    expect(screen.getByText("Selected")).toBeInTheDocument();

    await user.click(button);

    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
