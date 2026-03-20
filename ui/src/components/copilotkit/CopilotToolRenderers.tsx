"use client";

import type { ReactElement } from "react";

import { useCatalogToolRenderers } from "@/components/copilotkit/renderers/useCatalogToolRenderers";
import { useDefaultToolRenderer } from "@/components/copilotkit/renderers/useDefaultToolRenderer";
import { useImageAnalysisToolRenderers } from "@/components/copilotkit/renderers/useImageAnalysisToolRenderers";
import type { BundleProposal } from "@/lib/bundleProposalsStore";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";

type CopilotToolRenderersProps = {
  onBundleSelected?: (bundleId: string) => void;
  roomId?: string | null;
  threadId?: string | null;
  onFloorPlanRendered?: (snapshot: Omit<FloorPlanPreviewState, "threadId">) => void;
  onBundleProposed?: (proposal: BundleProposal) => void;
};

export function CopilotToolRenderers({
  onBundleSelected,
  roomId,
  threadId,
  onFloorPlanRendered,
  onBundleProposed,
}: CopilotToolRenderersProps): ReactElement | null {
  useDefaultToolRenderer();
  useCatalogToolRenderers({
    ...(onBundleSelected ? { onBundleSelected } : {}),
    ...(onFloorPlanRendered ? { onFloorPlanRendered } : {}),
    ...(onBundleProposed ? { onBundleProposed } : {}),
  });
  useImageAnalysisToolRenderers({
    ...(roomId !== undefined ? { roomId } : {}),
    ...(threadId !== undefined ? { threadId } : {}),
  });

  return null;
}
