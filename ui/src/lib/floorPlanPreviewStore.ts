import type { AttachmentRef } from "@/lib/attachments";

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
};

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
  return JSON.parse(raw) as FloorPlanPreviewState;
}

export function saveFloorPlanPreview(snapshot: FloorPlanPreviewState): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(floorPlanPreviewKey(snapshot.threadId), JSON.stringify(snapshot));
}
