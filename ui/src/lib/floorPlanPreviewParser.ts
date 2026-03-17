import { z } from "zod";

import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import { floorPlanSceneSchema, floorPlanSceneSummarySchema } from "@/lib/floorPlanScene";
import {
  attachmentRefSchema,
  extractToolFailureMessage,
  normalizeAttachmentRef,
  parseImageToolOutput,
  parseResult,
} from "@/lib/toolResultParsing";

type FloorPlanSnapshot = Omit<FloorPlanPreviewState, "threadId">;

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

function parseFloorPlanResult(result: unknown): z.infer<typeof floorPlanResultSchema> | null {
  const validated = floorPlanResultSchema.safeParse(parseResult(result));
  return validated.success ? validated.data : null;
}

export type FloorPlanBridgeStatus = "queued" | "executing" | "complete" | "failed";

export function buildFloorPlanSnapshot(
  status: FloorPlanBridgeStatus,
  result: unknown,
): FloorPlanSnapshot | null {
  const failureMessage = extractToolFailureMessage(result);
  const imageOutput = parseImageToolOutput(result);
  const floorPlanResult = parseFloorPlanResult(result);
  const rawParsed = parseResult(result);
  const parsedScene =
    typeof rawParsed === "object" && rawParsed !== null && "scene" in rawParsed
      ? floorPlanSceneSchema.safeParse((rawParsed as { scene: unknown }).scene)
      : null;
  const parsedSummary =
    typeof rawParsed === "object" && rawParsed !== null && "scene_summary" in rawParsed
      ? floorPlanSceneSummarySchema.safeParse(
          (rawParsed as { scene_summary: unknown }).scene_summary,
        )
      : null;
  if (status !== "complete" || failureMessage || !imageOutput) {
    return null;
  }
  return {
    caption: floorPlanResult?.caption ?? imageOutput.caption,
    images: imageOutput.images.map(normalizeAttachmentRef),
    sceneRevision: floorPlanResult?.scene_revision ?? 0,
    sceneLevel: floorPlanResult?.scene_level ?? "baseline",
    warnings: floorPlanResult?.warnings ?? [],
    legendItems: floorPlanResult?.legend_items ?? [],
    scene: parsedScene?.success ? parsedScene.data : null,
    sceneSummary: parsedSummary?.success ? parsedSummary.data : null,
  };
}
