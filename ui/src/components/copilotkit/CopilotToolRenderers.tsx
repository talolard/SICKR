"use client";

import { useEffect, useMemo } from "react";
import type { ReactElement } from "react";
import { useDefaultRenderTool, useRenderTool } from "@copilotkit/react-core/v2";
import { z } from "zod";

import { BundleProposalToolRenderer } from "@/components/tooling/BundleProposalToolRenderer";
import {
  DepthEstimationToolRenderer,
  type DepthEstimationToolResult,
} from "@/components/tooling/DepthEstimationToolRenderer";
import { DefaultToolCallRenderer } from "@/components/tooling/DefaultToolCallRenderer";
import { ImageToolOutputRenderer } from "@/components/tooling/ImageToolOutputRenderer";
import {
  ObjectDetectionToolRenderer,
  type ObjectDetectionToolResult,
} from "@/components/tooling/ObjectDetectionToolRenderer";
import {
  RoomPhotoAnalysisToolRenderer,
  type RoomPhotoAnalysisToolResult,
} from "@/components/tooling/RoomPhotoAnalysisToolRenderer";
import {
  SegmentationToolRenderer,
  type SegmentationToolResult,
} from "@/components/tooling/SegmentationToolRenderer";
import { createAnalysisFeedback } from "@/lib/api/threadDataClient";
import type { AttachmentRef } from "@/lib/attachments";
import type { BundleProposal } from "@/lib/bundleProposalsStore";
import { publishFloorPlanRendered } from "@/lib/floorPlanPreviewEvents";
import {
  buildFloorPlanSnapshot,
  type FloorPlanBridgeStatus,
} from "@/lib/floorPlanPreviewParser";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";

type ImageToolOutput = {
  caption: string;
  images: AttachmentRef[];
};

const attachmentRefSchema = z.object({
  attachment_id: z.string(),
  mime_type: z.string(),
  uri: z.string(),
  width: z.number().nullable(),
  height: z.number().nullable(),
  file_name: z.string().nullable().optional(),
});

const imageToolOutputSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
});
const roomPhotoAnalysisSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
  room_hints: z.array(z.string()),
});
const objectDetectionSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
  detections: z.array(
    z.object({
      label: z.string(),
      bbox_xyxy_px: z.tuple([z.number(), z.number(), z.number(), z.number()]),
      bbox_xyxy_norm: z.tuple([z.number(), z.number(), z.number(), z.number()]),
    }),
  ),
});
const depthEstimationSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
  parameters_used: z.object({
    ensemble_size: z.number(),
    processing_res: z.number(),
    resample_method: z.enum(["bilinear", "nearest", "bicubic"]),
    seed: z.number(),
    output_format: z.enum(["png", "jpg", "webp"]),
  }),
});
const segmentationSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
  prompt: z.string(),
  queries: z.array(z.string()).default([]),
  query_results: z
    .array(
      z.object({
        query: z.string(),
        status: z.enum(["matched", "unattributed", "no_match"]),
        matched_mask_count: z.number(),
      }),
    )
    .default([]),
  analysis_id: z.string().nullable().optional(),
  masks: z.array(
    z.object({
      label: z.string(),
      query: z.string().nullable().optional(),
      score: z.number().nullable().optional(),
      bbox_xyxy_px: z
        .tuple([z.number(), z.number(), z.number(), z.number()])
        .nullable()
        .optional(),
      mask_image: attachmentRefSchema,
    }),
  ),
});
const floorPlanResultSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
  scene_revision: z.number(),
  scene_level: z.enum(["baseline", "detailed"]),
  warnings: z
    .array(
      z.object({
        severity: z.enum(["info", "warn", "error"]),
        code: z.string(),
        message: z.string(),
        entity_id: z.string().nullable().optional(),
      }),
    )
    .optional(),
  legend_items: z.array(z.string()).optional(),
});
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

type ParsedAttachmentRef = z.infer<typeof attachmentRefSchema>;

function parseResult(result: unknown): unknown {
  if (typeof result !== "string") {
    return unwrapToolReturnValue(result);
  }
  try {
    return unwrapToolReturnValue(JSON.parse(result) as unknown);
  } catch {
    return result;
  }
}

function unwrapToolReturnValue(result: unknown): unknown {
  if (typeof result !== "object" || result === null) {
    return result;
  }
  if ("return_value" in result) {
    return (result as { return_value: unknown }).return_value;
  }
  if ("result" in result) {
    return (result as { result: unknown }).result;
  }
  return result;
}

function normalizeAttachmentRef(parsed: ParsedAttachmentRef): AttachmentRef {
  const normalized: AttachmentRef = {
    attachment_id: parsed.attachment_id,
    mime_type: parsed.mime_type,
    uri: parsed.uri,
    width: parsed.width,
    height: parsed.height,
  };
  if (parsed.file_name !== undefined) {
    normalized.file_name = parsed.file_name;
  }
  return normalized;
}

function parseAttachmentList(result: unknown): AttachmentRef[] | null {
  const parsed = parseResult(result);
  if (!Array.isArray(parsed)) {
    return null;
  }
  const validated = z.array(attachmentRefSchema).safeParse(parsed);
  return validated.success ? validated.data.map(normalizeAttachmentRef) : null;
}

function parseImageToolOutput(result: unknown): ImageToolOutput | null {
  const validated = imageToolOutputSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
  };
}

function looksLikeToolFailure(result: unknown): result is string {
  const parsed = parseResult(result);
  if (
    typeof parsed === "object" &&
    parsed !== null &&
    "status" in parsed &&
    parsed.status === "error"
  ) {
    return true;
  }
  if (typeof parsed !== "string") {
    return false;
  }
  return (
    /validation errors?/i.test(parsed) ||
    /tool failed/i.test(parsed) ||
    /missing_terminal_event/i.test(parsed) ||
    /terminated/i.test(parsed)
  );
}

function extractToolFailureMessage(result: unknown): string | undefined {
  const parsed = parseResult(result);
  if (
    typeof parsed === "object" &&
    parsed !== null &&
    "status" in parsed &&
    parsed.status === "error"
  ) {
    const message =
      "message" in parsed && typeof parsed.message === "string"
        ? parsed.message
        : "Tool run failed.";
    const reason =
      "reason" in parsed && typeof parsed.reason === "string"
        ? parsed.reason
        : undefined;
    return reason ? `${message} (${reason})` : message;
  }
  if (typeof parsed === "string" && looksLikeToolFailure(parsed)) {
    return parsed;
  }
  return undefined;
}

function parseRoomPhotoAnalysisResult(result: unknown): RoomPhotoAnalysisToolResult | null {
  const validated = roomPhotoAnalysisSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
    room_hints: validated.data.room_hints,
  };
}

function parseObjectDetectionResult(result: unknown): ObjectDetectionToolResult | null {
  const validated = objectDetectionSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
    detections: validated.data.detections,
  };
}

function parseDepthEstimationResult(result: unknown): DepthEstimationToolResult | null {
  const validated = depthEstimationSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
    parameters_used: validated.data.parameters_used,
  };
}

function parseSegmentationResult(result: unknown): SegmentationToolResult | null {
  const validated = segmentationSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
    prompt: validated.data.prompt,
    queries: validated.data.queries,
    query_results: validated.data.query_results,
    analysis_id: validated.data.analysis_id ?? null,
    masks: validated.data.masks.map((mask) => ({
      label: mask.label,
      query: mask.query ?? null,
      score: mask.score ?? null,
      bbox_xyxy_px: mask.bbox_xyxy_px ?? null,
      mask_image: normalizeAttachmentRef(mask.mask_image),
    })),
  };
}

function parseFloorPlanResult(result: unknown): z.infer<typeof floorPlanResultSchema> | null {
  const validated = floorPlanResultSchema.safeParse(parseResult(result));
  return validated.success ? validated.data : null;
}

type CopilotToolRenderersProps = {
  threadId?: string | null;
  onFloorPlanRendered?: (snapshot: Omit<FloorPlanPreviewState, "threadId">) => void;
  onBundleProposed?: (proposal: BundleProposal) => void;
};

type FloorPlanSnapshot = Omit<FloorPlanPreviewState, "threadId">;

type FloorPlanRenderBridgeProps = {
  status: FloorPlanBridgeStatus;
  result: unknown;
  onFloorPlanRendered?: (snapshot: FloorPlanSnapshot) => void;
};

function FloorPlanRenderBridge({
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
    return (
      <div className="rounded border bg-white p-2">
        <p className="text-sm text-gray-700">Rendering floor plan...</p>
      </div>
    );
  }
  if (failureMessage) {
    return (
      <div className="rounded border bg-white p-2">
        <DefaultToolCallRenderer
          name="render_floor_plan"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage={failureMessage}
        />
      </div>
    );
  }
  if (!imageOutput) {
    if (floorPlanResult) {
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name="render_floor_plan"
            status="complete"
            result={floorPlanResult}
            args={undefined}
            errorMessage={undefined}
          />
        </div>
      );
    }
    return (
      <div className="rounded border bg-white p-2">
        <DefaultToolCallRenderer
          name="render_floor_plan"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage="Tool returned an invalid floor-plan payload."
        />
      </div>
    );
  }
  return (
    <div className="rounded border bg-white p-2">
      <ImageToolOutputRenderer caption={imageOutput.caption} images={imageOutput.images} />
    </div>
  );
}

type BundleProposalBridgeProps = {
  status: "queued" | "executing" | "complete";
  result: unknown;
  onBundleProposed?: (proposal: BundleProposal) => void;
};

function BundleProposalBridge({
  status,
  result,
  onBundleProposed,
}: BundleProposalBridgeProps): ReactElement {
  const parsed = bundleProposalSchema.safeParse(parseResult(result));

  useEffect(() => {
    if (status !== "complete" || !parsed.success) {
      return;
    }
    onBundleProposed?.(parsed.data);
  }, [onBundleProposed, parsed, status]);

  if (status !== "complete") {
    return (
      <div className="rounded border bg-white p-2">
        <p className="text-sm text-gray-700">Building bundle proposal...</p>
      </div>
    );
  }
  if (!parsed.success) {
    return (
      <div className="rounded border bg-white p-2">
        <DefaultToolCallRenderer
          name="propose_bundle"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage="Tool returned an invalid bundle payload."
        />
      </div>
    );
  }
  return <BundleProposalToolRenderer />;
}

export function CopilotToolRenderers({
  threadId,
  onFloorPlanRendered,
  onBundleProposed,
}: CopilotToolRenderersProps): ReactElement | null {
  useDefaultRenderTool({
    render: ({ name, status, result, parameters }) => {
      const parsedResult = parseResult(result);
      const mappedStatusBase =
        status === "inProgress" ? "queued" : status === "executing" ? "executing" : "complete";
      const mappedStatus =
        mappedStatusBase === "complete" && looksLikeToolFailure(parsedResult)
          ? "failed"
          : mappedStatusBase;
      const failureMessage = extractToolFailureMessage(parsedResult);
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name={name}
            status={mappedStatus}
            result={mappedStatus === "failed" ? undefined : parsedResult}
            args={parameters}
            errorMessage={mappedStatus === "failed" ? failureMessage : undefined}
          />
        </div>
      );
    },
  });

  useRenderTool({
    name: "run_search_graph",
    parameters: z.object({
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
    }),
    render: ({ status, result, parameters }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Searching IKEA catalog...</p>
          </div>
        );
      }
      const failureMessage = extractToolFailureMessage(result);
      if (failureMessage) {
        return (
          <div className="rounded border bg-white p-2">
            <DefaultToolCallRenderer
              name="run_search_graph"
              status="failed"
              result={undefined}
              args={parameters}
              errorMessage={failureMessage}
            />
          </div>
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name="run_search_graph"
            status="complete"
            result={parseResult(result)}
            args={parameters}
            errorMessage={undefined}
          />
        </div>
      );
    },
  });

  useRenderTool({
    name: "propose_bundle",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      const mappedStatus =
        status === "inProgress" ? "queued" : status === "executing" ? "executing" : "complete";
      return (
        <BundleProposalBridge
          status={mappedStatus}
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
      const mappedStatus =
        status === "inProgress" ? "queued" : status === "executing" ? "executing" : "complete";
      return (
        <FloorPlanRenderBridge
          status={mappedStatus}
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
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Inspecting uploaded images...</p>
          </div>
        );
      }
      const images = parseAttachmentList(result);
      if (!images) {
        return (
          <div className="rounded border bg-white p-2">
            <DefaultToolCallRenderer
              name="list_uploaded_images"
              status="complete"
              result={result}
              args={undefined}
              errorMessage={undefined}
            />
          </div>
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <ImageToolOutputRenderer caption="Uploaded images" images={images} />
        </div>
      );
    },
  });

  useRenderTool({
    name: "generate_floor_plan_preview_image",
    parameters: z.object({}),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Generating preview image...</p>
          </div>
        );
      }
      const imageOutput = parseImageToolOutput(result);
      if (!imageOutput) {
        return (
          <div className="rounded border bg-white p-2">
            <DefaultToolCallRenderer
              name="generate_floor_plan_preview_image"
              status="complete"
              result={result}
              args={undefined}
              errorMessage={undefined}
            />
          </div>
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <ImageToolOutputRenderer caption={imageOutput.caption} images={imageOutput.images} />
        </div>
      );
    },
  });

  useRenderTool({
    name: "detect_objects_in_image",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Detecting room objects...</p>
          </div>
        );
      }
      const parsed = parseObjectDetectionResult(result);
      if (parsed) {
        return <ObjectDetectionToolRenderer result={parsed} />;
      }
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name="detect_objects_in_image"
            status="failed"
            result={undefined}
            args={undefined}
            errorMessage="Tool returned an invalid object-detection payload."
          />
        </div>
      );
    },
  });

  useRenderTool({
    name: "estimate_depth_map",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Estimating depth map...</p>
          </div>
        );
      }
      const parsed = parseDepthEstimationResult(result);
      if (parsed) {
        return <DepthEstimationToolRenderer result={parsed} />;
      }
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name="estimate_depth_map"
            status="failed"
            result={undefined}
            args={undefined}
            errorMessage="Tool returned an invalid depth payload."
          />
        </div>
      );
    },
  });

  useRenderTool({
    name: "segment_image_with_prompt",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Segmenting image...</p>
          </div>
        );
      }
      const parsed = parseSegmentationResult(result);
      if (parsed) {
        const canPersistFeedback = Boolean(threadId) && Boolean(parsed.analysis_id);
        return (
          <SegmentationToolRenderer
            result={parsed}
            {...(canPersistFeedback
              ? {
                  onSubmitFeedback: async (payload) => {
                    await createAnalysisFeedback({
                      threadId: threadId as string,
                      analysisId: parsed.analysis_id as string,
                      payload: {
                        feedback_kind: payload.feedbackKind,
                        mask_ordinal: payload.maskOrdinal,
                        mask_label: payload.maskLabel,
                        ...(payload.queryText ? { query_text: payload.queryText } : {}),
                      },
                    });
                  },
                }
              : {})}
          />
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name="segment_image_with_prompt"
            status="failed"
            result={undefined}
            args={undefined}
            errorMessage="Tool returned an invalid segmentation payload."
          />
        </div>
      );
    },
  });

  useRenderTool({
    name: "analyze_room_photo",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Analyzing room photo...</p>
          </div>
        );
      }
      const parsed = parseRoomPhotoAnalysisResult(result);
      if (parsed) {
        return <RoomPhotoAnalysisToolRenderer result={parsed} />;
      }
      const parsedResult = parseResult(result);
      const errorMessage =
        typeof parsedResult === "string"
          ? parsedResult
          : "Tool returned an invalid room-analysis payload.";
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name="analyze_room_photo"
            status="failed"
            result={undefined}
            args={undefined}
            errorMessage={errorMessage}
          />
        </div>
      );
    },
  });

  return null;
}
