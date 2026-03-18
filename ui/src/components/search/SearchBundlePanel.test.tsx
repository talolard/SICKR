import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { SearchBundlePanel } from "./SearchBundlePanel";

const longNotes = [
  "Portable lighting for the hallway without drilling.",
  "Use adhesive-friendly pieces and keep the explanation fully visible.",
  "Make the summary easy to scan before opening the detailed items.",
].join(" ");

const proposal = {
  bundle_id: "bundle-1",
  title: "Desk setup",
  notes: longNotes,
  budget_cap_eur: 200,
  items: [
    {
      item_id: "chair-1",
      product_name: "Chair One",
      product_url: "https://www.ikea.com/de/de/p/chair-one-12345678/",
      description_text: "Desk chair",
      price_eur: 79.99,
      quantity: 2,
      line_total_eur: 159.98,
      reason: "Two matching chairs",
      image_urls: [
        "/static/product-images/chair-1",
        "/static/product-images/chair-1/2",
      ],
    },
    {
      item_id: "lamp-1",
      product_name: "Lamp One",
      product_url: null,
      description_text: "Task lamp",
      price_eur: 29.99,
      quantity: 1,
      line_total_eur: 29.99,
      reason: "Desk lighting",
      image_urls: [],
    },
  ],
  bundle_total_eur: 189.97,
  validations: [
    {
      kind: "pricing_complete" as const,
      status: "pass" as const,
      message: "All bundle items have prices, so the total is complete.",
    },
    {
      kind: "duplicate_items" as const,
      status: "warn" as const,
      message: "Merged 1 repeated product entry into combined quantities.",
    },
  ],
  created_at: "2026-03-11T11:00:00Z",
  run_id: "run-1",
};

describe("SearchBundlePanel", () => {
  it("renders empty state when there are no proposals", () => {
    render(<SearchBundlePanel proposals={[]} />);

    expect(screen.getByText("Bundles")).toBeInTheDocument();
    expect(screen.getByText(/will appear here/i)).toBeInTheDocument();
  });

  it("renders collapsed bundle summaries with totals by default", () => {
    render(<SearchBundlePanel proposals={[proposal]} />);

    expect(screen.getByText("Desk setup")).toBeInTheDocument();
    expect(screen.getByText("€189.97")).toBeInTheDocument();
    expect(screen.getByText("2 items")).toBeInTheDocument();
    expect(screen.queryByText("Two matching chairs")).not.toBeInTheDocument();
    expect(screen.getByText("Scroll to read the full explanation.")).toBeInTheDocument();
    expect(screen.getByTestId("bundle-summary-notes")).toHaveClass("overflow-y-auto");
    expect(screen.getByRole("button", { name: /desk setup/i })).toHaveClass("cursor-pointer");
  });

  it("reveals pricing table details, thumbnails, and rationale when expanded", async () => {
    const user = userEvent.setup();

    render(<SearchBundlePanel proposals={[proposal]} />);

    await user.click(screen.getByRole("button", { name: /desk setup/i }));

    expect(screen.getAllByText("Why it is in the bundle")).toHaveLength(2);
    expect(screen.getByText("Two matching chairs")).toBeInTheDocument();
    expect(screen.getByText("Chair One")).toBeInTheDocument();
    expect(screen.getByText(/Pricing:/)).toBeInTheDocument();
    expect(screen.getByText(/Duplicates:/)).toBeInTheDocument();
    expect(screen.getAllByText("Unit")).toHaveLength(2);
    expect(screen.getAllByText("Qty")).toHaveLength(2);
    expect(screen.getAllByText("Total")).toHaveLength(3);
    expect(screen.getByTestId("bundle-items-bundle-1")).toHaveClass("max-h-96", "overflow-y-auto");
    expect(screen.getByTestId("bundle-item-bundle-1-chair-1-button")).toBeInTheDocument();
    expect(screen.getByTestId("bundle-item-bundle-1-lamp-1-placeholder")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open product page for Chair One" })).toHaveAttribute(
      "href",
      "https://www.ikea.com/de/de/p/chair-one-12345678/",
    );
  });

  it("opens the bundle item gallery popover", async () => {
    const user = userEvent.setup();

    render(<SearchBundlePanel proposals={[proposal]} />);

    await user.click(screen.getByRole("button", { name: /desk setup/i }));
    await user.click(screen.getByTestId("bundle-item-bundle-1-chair-1-button"));

    expect(screen.getByTestId("bundle-item-bundle-1-chair-1-popover")).toBeInTheDocument();
    expect(screen.getByText("Image 1 of 2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(screen.getByText("Image 2 of 2")).toBeInTheDocument();
  });

  it("expands and highlights the active bundle when selected from chat", () => {
    const scrollIntoView = vi.fn();
    const originalRequestAnimationFrame = window.requestAnimationFrame;
    const originalScrollIntoView = window.HTMLElement.prototype.scrollIntoView;
    window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
    window.requestAnimationFrame = ((callback: FrameRequestCallback): number => {
      callback(0);
      return 1;
    }) as typeof window.requestAnimationFrame;

    render(<SearchBundlePanel activeBundleId="bundle-1" proposals={[proposal]} />);

    expect(screen.getByText("Selected")).toBeInTheDocument();
    expect(screen.getByText("Two matching chairs")).toBeInTheDocument();
    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "nearest" });

    window.requestAnimationFrame = originalRequestAnimationFrame;
    window.HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
  });
});
