import type { ReactElement } from "react";

import { BundleProposalSummaryCard } from "@/components/search/BundleProposalSummaryCard";
import type { BundleProposal } from "@/lib/bundleProposalsStore";

type BundleProposalToolRendererProps = {
  onOpenBundle?: (() => void) | undefined;
  proposal: BundleProposal;
};

export function BundleProposalToolRenderer({
  onOpenBundle,
  proposal,
}: BundleProposalToolRendererProps): ReactElement {
  return (
    <BundleProposalSummaryCard
      actionLabel={onOpenBundle ? "Open bundle details" : "Saved to bundles panel"}
      {...(onOpenBundle ? { onClick: onOpenBundle } : {})}
      proposal={proposal}
    />
  );
}
