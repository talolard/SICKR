import { z } from "zod";

const BUNDLE_PROPOSALS_PREFIX = "copilotkit_ui_bundle_proposals_";

export const bundleValidationSchema = z.object({
  kind: z.enum(["budget_max_eur", "pricing_complete", "duplicate_items"]),
  status: z.enum(["pass", "warn", "fail", "unknown"]),
  message: z.string(),
});

export const bundleProposalItemSchema = z.object({
  item_id: z.string(),
  product_name: z.string(),
  product_url: z.string().nullable().default(null),
  description_text: z.string().nullable(),
  price_eur: z.number().nullable(),
  quantity: z.number(),
  line_total_eur: z.number().nullable(),
  reason: z.string(),
  image_urls: z.array(z.string()).default([]),
});

export const bundleProposalSchema = z.object({
  bundle_id: z.string(),
  title: z.string(),
  notes: z.string().nullable(),
  budget_cap_eur: z.number().nullable(),
  items: z.array(bundleProposalItemSchema),
  bundle_total_eur: z.number().nullable(),
  validations: z.array(bundleValidationSchema),
  created_at: z.string(),
  run_id: z.string().nullable(),
});

export type BundleProposal = z.infer<typeof bundleProposalSchema>;

function storageKey(threadId: string): string {
  return `${BUNDLE_PROPOSALS_PREFIX}${threadId}`;
}

function sortNewestFirst(proposals: BundleProposal[]): BundleProposal[] {
  return [...proposals].sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

export function mergeBundleProposals(
  ...proposalLists: readonly BundleProposal[][]
): BundleProposal[] {
  const merged = new Map<string, BundleProposal>();
  for (const proposals of proposalLists) {
    for (const proposal of proposals) {
      if (!merged.has(proposal.bundle_id)) {
        merged.set(proposal.bundle_id, proposal);
      }
    }
  }
  return sortNewestFirst([...merged.values()]);
}

function parseBundleProposalArray(raw: string): BundleProposal[] {
  const decoded = JSON.parse(raw) as unknown;
  const parsed = z.array(bundleProposalSchema).safeParse(decoded);
  return parsed.success ? sortNewestFirst(parsed.data) : [];
}

export function loadBundleProposals(threadId: string): BundleProposal[] {
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(storageKey(threadId));
  if (!raw) {
    return [];
  }
  try {
    return parseBundleProposalArray(raw);
  } catch {
    return [];
  }
}

export function saveBundleProposals(threadId: string, proposals: BundleProposal[]): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(storageKey(threadId), JSON.stringify(sortNewestFirst(proposals)));
}

export function replaceBundleProposals(
  threadId: string,
  proposals: BundleProposal[],
): BundleProposal[] {
  const next = sortNewestFirst(proposals);
  saveBundleProposals(threadId, next);
  return next;
}

export function appendBundleProposal(
  threadId: string,
  proposal: BundleProposal,
): BundleProposal[] {
  const next = mergeBundleProposals([proposal], loadBundleProposals(threadId));
  saveBundleProposals(threadId, next);
  return next;
}
