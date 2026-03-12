"use client";

import type { ReactElement } from "react";
import type { BundleProposal } from "@/lib/bundleProposalsStore";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import { useCatalogToolRenderers } from "@/components/copilotkit/renderers/useCatalogToolRenderers";
import { useDefaultToolRenderer } from "@/components/copilotkit/renderers/useDefaultToolRenderer";
import { useImageAnalysisToolRenderers } from "@/components/copilotkit/renderers/useImageAnalysisToolRenderers";

type CopilotToolRenderersProps = {
  threadId?: string | null;
  onFloorPlanRendered?: (snapshot: Omit<FloorPlanPreviewState, "threadId">) => void;
  onBundleProposed?: (proposal: BundleProposal) => void;
};

export function CopilotToolRenderers({
  threadId,
  onFloorPlanRendered,
  onBundleProposed,
}: CopilotToolRenderersProps): ReactElement | null {
  useDefaultToolRenderer();
  useCatalogToolRenderers({
    ...(onFloorPlanRendered ? { onFloorPlanRendered } : {}),
    ...(onBundleProposed ? { onBundleProposed } : {}),
  });
  useImageAnalysisToolRenderers({
    ...(threadId !== undefined ? { threadId } : {}),
  });

  return null;
}
