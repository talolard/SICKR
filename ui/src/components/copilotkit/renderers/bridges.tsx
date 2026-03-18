"use client";

import { useEffect, useMemo } from "react";
import type { ReactElement } from "react";

import { BundleProposalToolRenderer } from "@/components/tooling/BundleProposalToolRenderer";
import { ImageToolOutputRenderer } from "@/components/tooling/ImageToolOutputRenderer";
import { bundleProposalSchema, type BundleProposal } from "@/lib/bundleProposalsStore";
import { publishFloorPlanRendered } from "@/lib/floorPlanPreviewEvents";
import {
  buildFloorPlanSnapshot,
  type FloorPlanBridgeStatus,
} from "@/lib/floorPlanPreviewParser";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import {
  extractToolFailureMessage,
  parseImageToolOutput,
  parseResult,
} from "@/lib/toolResultParsing";

import { parseFloorPlanResult } from "./parsing";
import { DefaultToolCard, LoadingToolMessage, ToolCard } from "./shared";

type FloorPlanSnapshot = Omit<FloorPlanPreviewState, "threadId">;

type FloorPlanRenderBridgeProps = {
  status: FloorPlanBridgeStatus;
  result: unknown;
  onFloorPlanRendered?: (snapshot: FloorPlanSnapshot) => void;
};

type BundleProposalBridgeProps = {
  status: "queued" | "executing" | "complete" | "failed";
  result: unknown;
  onBundleProposed?: (proposal: BundleProposal) => void;
};

export function FloorPlanRenderBridge({
  status,
  result,
  onFloorPlanRendered,
}: FloorPlanRenderBridgeProps): ReactElement {
  const failureMessage = extractToolFailureMessage(result);
  const imageOutput = parseImageToolOutput(result);
  const floorPlanResult = parseFloorPlanResult(result);

  const snapshot = useMemo<FloorPlanSnapshot | null>(() => {
    return buildFloorPlanSnapshot(status, result);
  }, [result, status]);

  useEffect(() => {
    if (!snapshot) {
      return;
    }
    publishFloorPlanRendered(snapshot);
    onFloorPlanRendered?.(snapshot);
  }, [onFloorPlanRendered, snapshot]);

  if (status !== "complete") {
    return <LoadingToolMessage message="Rendering floor plan..." />;
  }
  if (failureMessage) {
    return (
      <DefaultToolCard
        name="render_floor_plan"
        status="failed"
        result={undefined}
        args={undefined}
        errorMessage={failureMessage}
      />
    );
  }
  if (!imageOutput) {
    if (floorPlanResult) {
      return (
        <DefaultToolCard
          name="render_floor_plan"
          status="complete"
          result={floorPlanResult}
          args={undefined}
          errorMessage={undefined}
        />
      );
    }
    return (
      <DefaultToolCard
        name="render_floor_plan"
        status="failed"
        result={undefined}
        args={undefined}
        errorMessage="Tool returned an invalid floor-plan payload."
      />
    );
  }
  return (
    <ToolCard>
      <ImageToolOutputRenderer caption={imageOutput.caption} images={imageOutput.images} />
    </ToolCard>
  );
}

export function BundleProposalBridge({
  status,
  result,
  onBundleProposed,
}: BundleProposalBridgeProps): ReactElement {
  const failureMessage = extractToolFailureMessage(result);
  const parsed = bundleProposalSchema.safeParse(parseResult(result));

  useEffect(() => {
    if (status !== "complete" || !parsed.success) {
      return;
    }
    onBundleProposed?.(parsed.data);
  }, [onBundleProposed, parsed, status]);

  if (failureMessage) {
    return (
      <DefaultToolCard
        name="propose_bundle"
        status="failed"
        result={undefined}
        args={undefined}
        errorMessage={failureMessage}
      />
    );
  }
  if (status !== "complete") {
    return <LoadingToolMessage message="Building bundle proposal..." />;
  }
  if (!parsed.success) {
    return (
      <DefaultToolCard
        name="propose_bundle"
        status="failed"
        result={undefined}
        args={undefined}
        errorMessage="Tool returned an invalid bundle payload."
      />
    );
  }
  return <BundleProposalToolRenderer proposal={parsed.data} />;
}
