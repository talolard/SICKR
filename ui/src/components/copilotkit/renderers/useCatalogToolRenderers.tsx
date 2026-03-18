"use client";

import { useRenderTool } from "@copilotkit/react-core/v2";
import { z } from "zod";

import { ImageToolOutputRenderer } from "@/components/tooling/ImageToolOutputRenderer";
import {
  ProductResultsToolRenderer,
  type QueryDisplayMetadata,
} from "@/components/tooling/ProductResultsToolRenderer";
import type { BundleProposal } from "@/lib/bundleProposalsStore";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import { parseSearchResultGroups } from "@/lib/productResults";
import {
  extractToolFailureMessage,
  parseAttachmentList,
  parseImageToolOutput,
  parseResult,
} from "@/lib/toolResultParsing";

import { BundleProposalBridge, FloorPlanRenderBridge } from "./bridges";
import {
  DefaultToolCard,
  LoadingToolMessage,
  ToolCard,
  mapCopilotToolStatus,
} from "./shared";

type FloorPlanSnapshot = Omit<FloorPlanPreviewState, "threadId">;

type UseCatalogToolRenderersOptions = {
  onFloorPlanRendered?: ((snapshot: FloorPlanSnapshot) => void) | undefined;
  onBundleProposed?: ((proposal: BundleProposal) => void) | undefined;
};

const searchGraphParametersSchema = z.object({
  queries: z.array(
    z.object({
      query_id: z.string(),
      semantic_query: z.string(),
      limit: z.number().optional(),
      candidate_pool_limit: z.number().nullable().optional(),
      filters: z.unknown().optional(),
      enable_diversification: z.boolean().optional(),
      purpose: z.string().nullable().optional(),
    }),
  ),
});

function buildQueryDisplayMetadata(
  parameters: z.infer<typeof searchGraphParametersSchema>,
): QueryDisplayMetadata[] {
  return parameters.queries.map((query, index) => ({
    queryId: query.query_id,
    title:
      typeof query.purpose === "string" && query.purpose.trim().length > 0
        ? query.purpose.trim()
        : /^query-\d+$/u.test(query.query_id)
          ? `Query ${index + 1}`
          : query.query_id.replace(/[_-]+/gu, " ").trim() || `Query ${index + 1}`,
    queryText: query.semantic_query,
  }));
}

export function useCatalogToolRenderers({
  onFloorPlanRendered,
  onBundleProposed,
}: UseCatalogToolRenderersOptions): void {
  useRenderTool({
    name: "run_search_graph",
    parameters: searchGraphParametersSchema,
    render: ({ status, result, parameters }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Searching IKEA catalog..." />;
      }
      const failureMessage = extractToolFailureMessage(result);
      if (failureMessage) {
        return (
          <DefaultToolCard
            name="run_search_graph"
            status="failed"
            result={undefined}
            args={parameters}
            errorMessage={failureMessage}
          />
        );
      }
      const groups = parseSearchResultGroups(parseResult(result));
      if (!groups) {
        return (
          <DefaultToolCard
            name="run_search_graph"
            status="complete"
            result={parseResult(result)}
            args={parameters}
            errorMessage={undefined}
          />
        );
      }
      return (
        <ToolCard>
          <ProductResultsToolRenderer
            groups={groups}
            queryMetadata={buildQueryDisplayMetadata(parameters)}
          />
        </ToolCard>
      );
    },
  });

  useRenderTool({
    name: "propose_bundle",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      return (
        <BundleProposalBridge
          status={mapCopilotToolStatus(status)}
          result={result}
          {...(onBundleProposed ? { onBundleProposed } : {})}
        />
      );
    },
  });

  useRenderTool({
    name: "render_floor_plan",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      return (
        <FloorPlanRenderBridge
          status={mapCopilotToolStatus(status)}
          result={result}
          {...(onFloorPlanRendered ? { onFloorPlanRendered } : {})}
        />
      );
    },
  });

  useRenderTool({
    name: "list_uploaded_images",
    parameters: z.object({}),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Inspecting uploaded images..." />;
      }
      const images = parseAttachmentList(result);
      if (!images) {
        return (
          <DefaultToolCard
            name="list_uploaded_images"
            status="complete"
            result={result}
            args={undefined}
            errorMessage={undefined}
          />
        );
      }
      return (
        <ToolCard>
          <ImageToolOutputRenderer caption="Uploaded images" images={images} />
        </ToolCard>
      );
    },
  });

  useRenderTool({
    name: "generate_floor_plan_preview_image",
    parameters: z.object({}),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Generating preview image..." />;
      }
      const imageOutput = parseImageToolOutput(result);
      if (!imageOutput) {
        return (
          <DefaultToolCard
            name="generate_floor_plan_preview_image"
            status="complete"
            result={result}
            args={undefined}
            errorMessage={undefined}
          />
        );
      }
      return (
        <ToolCard>
          <ImageToolOutputRenderer caption={imageOutput.caption} images={imageOutput.images} />
        </ToolCard>
      );
    },
  });
}
