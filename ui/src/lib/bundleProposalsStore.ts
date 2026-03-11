import { z } from "zod";

const BUNDLE_PROPOSALS_PREFIX = "copilotkit_ui_bundle_proposals_";

export type BundleProposal = {
  bundle_id: string;
  title: string;
  notes: string | null;
  budget_cap_eur: number | null;
  items: Array<{
    item_id: string;
    product_name: string;
    description_text: string | null;
    price_eur: number | null;
    quantity: number;
    line_total_eur: number | null;
    reason: string;
  }>;
  bundle_total_eur: number | null;
  validations: Array<{
    kind: "budget_max_eur";
    status: "pass" | "fail" | "unknown";
    message: string;
  }>;
  created_at: string;
  run_id: string | null;
};

const bundleProposalSchema = z.object({
  bundle_id: z.string(),
  title: z.string(),
  notes: z.string().nullable(),
  budget_cap_eur: z.number().nullable(),
  items: z.array(
    z.object({
      item_id: z.string(),
      product_name: z.string(),
      description_text: z.string().nullable(),
      price_eur: z.number().nullable(),
      quantity: z.number(),
      line_total_eur: z.number().nullable(),
      reason: z.string(),
    }),
  ),
  bundle_total_eur: z.number().nullable(),
  validations: z.array(
    z.object({
      kind: z.enum(["budget_max_eur"]),
      status: z.enum(["pass", "fail", "unknown"]),
      message: z.string(),
    }),
  ),
  created_at: z.string(),
  run_id: z.string().nullable(),
});

function storageKey(threadId: string): string {
  return `${BUNDLE_PROPOSALS_PREFIX}${threadId}`;
}

export function loadBundleProposals(threadId: string): BundleProposal[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(storageKey(threadId));
  if (!raw) {
    return [];
  }
  const parsed = z.array(bundleProposalSchema).safeParse(JSON.parse(raw));
  return parsed.success ? parsed.data : [];
}

export function saveBundleProposals(threadId: string, proposals: BundleProposal[]): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKey(threadId), JSON.stringify(proposals));
}

export function appendBundleProposal(
  threadId: string,
  proposal: BundleProposal,
): BundleProposal[] {
  const current = loadBundleProposals(threadId);
  if (current.some((item) => item.bundle_id === proposal.bundle_id)) {
    return current;
  }
  const next = [proposal, ...current];
  saveBundleProposals(threadId, next);
  return next;
}
