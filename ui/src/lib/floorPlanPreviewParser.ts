import { z } from "zod";

import type { AttachmentRef } from "@/lib/attachments";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import { floorPlanSceneSchema, floorPlanSceneSummarySchema } from "@/lib/floorPlanScene";

type FloorPlanSnapshot = Omit<FloorPlanPreviewState, "threadId">;

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

function parseImageToolOutput(result: unknown): z.infer<typeof imageToolOutputSchema> | null {
  const validated = imageToolOutputSchema.safeParse(parseResult(result));
  return validated.success ? validated.data : null;
}

function parseFloorPlanResult(result: unknown): z.infer<typeof floorPlanResultSchema> | null {
  const validated = floorPlanResultSchema.safeParse(parseResult(result));
  return validated.success ? validated.data : null;
}

export type FloorPlanBridgeStatus = "queued" | "executing" | "complete" | "failed";

function normalizeAttachmentRef(
  parsed: z.infer<typeof attachmentRefSchema>,
): AttachmentRef {
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
