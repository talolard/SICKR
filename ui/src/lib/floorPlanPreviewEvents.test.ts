import {
  FLOOR_PLAN_RENDERED_EVENT_NAME,
  publishFloorPlanRendered,
  subscribeFloorPlanRendered,
} from "./floorPlanPreviewEvents";

describe("floorPlanPreviewEvents", () => {
  it("publishes and subscribes floor-plan rendered snapshots", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeFloorPlanRendered(listener);
    const rawListener = vi.fn();
    window.addEventListener(FLOOR_PLAN_RENDERED_EVENT_NAME, rawListener as EventListener);

    publishFloorPlanRendered({
      caption: "Rendered floor plan scene. Walls: 4, doors: 1, windows: 1, placements: 1.",
      images: [
        {
          attachment_id: "svg-1",
          mime_type: "image/svg+xml",
          uri: "/attachments/svg-1",
          width: null,
          height: null,
          file_name: "floor-plan.svg",
        },
      ],
      sceneRevision: 2,
      sceneLevel: "baseline",
      warnings: [],
      legendItems: ["Walls: dark strokes"],
    });

    expect(listener).toHaveBeenCalledTimes(1);
    expect(rawListener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0]?.[0]?.sceneRevision).toBe(2);
    expect(listener.mock.calls[0]?.[0]?.images[0]?.mime_type).toBe("image/svg+xml");

    unsubscribe();
    window.removeEventListener(FLOOR_PLAN_RENDERED_EVENT_NAME, rawListener as EventListener);
  });
});
