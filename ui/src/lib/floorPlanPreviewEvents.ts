import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";

export const FLOOR_PLAN_RENDERED_EVENT_NAME = "ikea-floorplan-rendered";

export type FloorPlanRenderedDetail = Omit<FloorPlanPreviewState, "threadId">;

export function publishFloorPlanRendered(detail: FloorPlanRenderedDetail): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent<FloorPlanRenderedDetail>(FLOOR_PLAN_RENDERED_EVENT_NAME, {
      detail,
    }),
  );
}

export function subscribeFloorPlanRendered(
  listener: (detail: FloorPlanRenderedDetail) => void,
): () => void {
  const handler: EventListener = (event) => {
    const customEvent = event as CustomEvent<FloorPlanRenderedDetail>;
    if (!customEvent.detail) {
      return;
    }
    listener(customEvent.detail);
  };
  window.addEventListener(FLOOR_PLAN_RENDERED_EVENT_NAME, handler);
  return () => {
    window.removeEventListener(FLOOR_PLAN_RENDERED_EVENT_NAME, handler);
  };
}
