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
});
