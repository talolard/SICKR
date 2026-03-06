import type { AttachmentRef } from "@/lib/attachments";
import type { FloorPlanScene, FloorPlanSceneSummary } from "@/lib/floorPlanScene";
import { floorPlanSceneSchema, floorPlanSceneSummarySchema } from "@/lib/floorPlanScene";
import { z } from "zod";

const FLOOR_PLAN_PREFIX = "copilotkit_ui_floor_plan_preview_";

export type FloorPlanPreviewState = {
  threadId: string;
  caption: string;
  images: AttachmentRef[];
  sceneRevision: number;
  sceneLevel: "baseline" | "detailed";
  warnings: Array<{
    severity: "info" | "warn" | "error";
    code: string;
    message: string;
    entity_id?: string | null | undefined;
  }>;
  legendItems: string[];
  scene: FloorPlanScene | null;
  sceneSummary: FloorPlanSceneSummary | null;
};

const floorPlanPreviewStateSchema = z.object({
  threadId: z.string(),
  caption: z.string(),
  images: z.array(
    z.object({
      attachment_id: z.string(),
      mime_type: z.string(),
      uri: z.string(),
      width: z.number().nullable(),
      height: z.number().nullable(),
      file_name: z.string().nullable().optional(),
    }),
  ),
  sceneRevision: z.number(),
  sceneLevel: z.enum(["baseline", "detailed"]),
  warnings: z.array(
    z.object({
      severity: z.enum(["info", "warn", "error"]),
      code: z.string(),
      message: z.string(),
      entity_id: z.string().nullable().optional(),
    }),
  ),
  legendItems: z.array(z.string()),
  scene: floorPlanSceneSchema.nullable().optional(),
  sceneSummary: floorPlanSceneSummarySchema.nullable().optional(),
});

function normalizeImages(
  images: z.infer<typeof floorPlanPreviewStateSchema>["images"],
): AttachmentRef[] {
  return images.map((image) => {
    const normalized: AttachmentRef = {
      attachment_id: image.attachment_id,
      mime_type: image.mime_type,
      uri: image.uri,
      width: image.width,
      height: image.height,
    };
    if (image.file_name !== undefined) {
      normalized.file_name = image.file_name;
    }
    return normalized;
  });
}

export function floorPlanPreviewKey(threadId: string): string {
  return `${FLOOR_PLAN_PREFIX}${threadId}`;
}

export function loadFloorPlanPreview(threadId: string): FloorPlanPreviewState | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(floorPlanPreviewKey(threadId));
  if (!raw) {
    return null;
  }
  const parsed = floorPlanPreviewStateSchema.safeParse(JSON.parse(raw));
  if (!parsed.success) {
    return null;
  }
  return {
    ...parsed.data,
    images: normalizeImages(parsed.data.images),
    scene: parsed.data.scene ?? null,
    sceneSummary: parsed.data.sceneSummary ?? null,
  };
}

export function saveFloorPlanPreview(snapshot: FloorPlanPreviewState): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(floorPlanPreviewKey(snapshot.threadId), JSON.stringify(snapshot));
}
