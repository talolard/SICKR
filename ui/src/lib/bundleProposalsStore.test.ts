import {
  appendBundleProposal,
  loadBundleProposals,
  mergeBundleProposals,
  replaceBundleProposals,
} from "./bundleProposalsStore";

describe("bundleProposalsStore", () => {
  const threadId = "thread-1";

  beforeEach(() => {
    window.localStorage.clear();
  });

  it("merges and sorts proposals newest-first without duplicates", () => {
    const older = {
      bundle_id: "bundle-1",
      title: "Older bundle",
      notes: null,
      budget_cap_eur: null,
      items: [],
      bundle_total_eur: null,
      validations: [],
      created_at: "2026-03-11T10:00:00Z",
      run_id: null,
    };
    const newer = {
      bundle_id: "bundle-2",
      title: "Newer bundle",
      notes: null,
      budget_cap_eur: null,
      items: [],
      bundle_total_eur: null,
      validations: [],
      created_at: "2026-03-11T11:00:00Z",
      run_id: null,
    };

    expect(mergeBundleProposals([older], [newer, older]).map((item) => item.bundle_id)).toEqual([
      "bundle-2",
      "bundle-1",
    ]);
  });

  it("replaces and appends persisted proposals", () => {
    const persisted = {
      bundle_id: "bundle-1",
      title: "Persisted bundle",
      notes: null,
      budget_cap_eur: null,
      items: [],
      bundle_total_eur: null,
      validations: [],
      created_at: "2026-03-11T10:00:00Z",
      run_id: null,
    };
    const newProposal = {
      ...persisted,
      bundle_id: "bundle-2",
      title: "Fresh bundle",
      created_at: "2026-03-11T12:00:00Z",
    };

    replaceBundleProposals(threadId, [persisted]);
    appendBundleProposal(threadId, newProposal);

    expect(loadBundleProposals(threadId).map((item) => item.bundle_id)).toEqual([
      "bundle-2",
      "bundle-1",
    ]);
  });

  it("backfills missing image_urls when loading persisted proposals", () => {
    window.localStorage.setItem(
      "copilotkit_ui_bundle_proposals_thread-1",
      JSON.stringify([
        {
          bundle_id: "bundle-1",
          title: "Persisted bundle",
          notes: null,
          budget_cap_eur: null,
          items: [
            {
              item_id: "chair-1",
              product_name: "Chair One",
              description_text: null,
              price_eur: 19.99,
              quantity: 1,
              line_total_eur: 19.99,
              reason: "Seat",
            },
          ],
          bundle_total_eur: 19.99,
          validations: [],
          created_at: "2026-03-11T10:00:00Z",
          run_id: null,
        },
      ]),
    );

    expect(loadBundleProposals(threadId)[0]?.items[0]?.image_urls).toEqual([]);
  });
});
