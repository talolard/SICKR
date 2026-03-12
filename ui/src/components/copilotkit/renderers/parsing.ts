import { z } from "zod";

import type { DepthEstimationToolResult } from "@/components/tooling/DepthEstimationToolRenderer";
import type { ObjectDetectionToolResult } from "@/components/tooling/ObjectDetectionToolRenderer";
import type { RoomPhotoAnalysisToolResult } from "@/components/tooling/RoomPhotoAnalysisToolRenderer";
import type { SegmentationToolResult } from "@/components/tooling/SegmentationToolRenderer";
import {
  attachmentRefSchema,
  normalizeAttachmentRef,
  parseResult,
} from "@/lib/toolResultParsing";

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

export type FloorPlanToolResult = z.infer<typeof floorPlanResultSchema>;

export function parseRoomPhotoAnalysisResult(result: unknown): RoomPhotoAnalysisToolResult | null {
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

export function parseObjectDetectionResult(result: unknown): ObjectDetectionToolResult | null {
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

export function parseDepthEstimationResult(result: unknown): DepthEstimationToolResult | null {
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

export function parseSegmentationResult(result: unknown): SegmentationToolResult | null {
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

export function parseFloorPlanResult(result: unknown): FloorPlanToolResult | null {
  const validated = floorPlanResultSchema.safeParse(parseResult(result));
  return validated.success ? validated.data : null;
}
