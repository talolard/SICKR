import { describe, expect, it } from "vitest";

import {
  floorPlanPreviewKey,
  loadFloorPlanPreview,
  saveFloorPlanPreview,
} from "./floorPlanPreviewStore";

describe("floorPlanPreviewStore", () => {
  it("loads legacy preview snapshots that do not include scene payload", () => {
    window.localStorage.setItem(
      floorPlanPreviewKey("thread-legacy"),
      JSON.stringify({
        threadId: "thread-legacy",
        caption: "Legacy floor plan",
        images: [],
        sceneRevision: 3,
        sceneLevel: "baseline",
        warnings: [],
        legendItems: [],
      }),
    );

    const loaded = loadFloorPlanPreview("thread-legacy");
    expect(loaded).not.toBeNull();
    expect(loaded?.scene).toBeNull();
    expect(loaded?.sceneSummary).toBeNull();
  });

  it("round-trips current preview snapshots with scene payload", () => {
    saveFloorPlanPreview({
      threadId: "thread-new",
      caption: "Detailed floor plan",
      images: [],
      sceneRevision: 4,
      sceneLevel: "detailed",
      warnings: [],
      legendItems: [],
      scene: {
        scene_level: "detailed",
        architecture: {
          dimensions_cm: { length_x_cm: 500, depth_y_cm: 350, height_z_cm: 260 },
          walls: [
            {
              wall_id: "w1",
              start_cm: { x_cm: 0, y_cm: 0 },
              end_cm: { x_cm: 500, y_cm: 0 },
            },
          ],
        },
      },
      sceneSummary: {
        wall_count: 4,
        door_count: 1,
        window_count: 1,
        placement_count: 2,
        fixture_count: 1,
        tagged_item_count: 0,
        has_outline: false,
      },
    });

    const loaded = loadFloorPlanPreview("thread-new");
    expect(loaded?.scene?.scene_level).toBe("detailed");
    expect(loaded?.sceneSummary?.wall_count).toBe(4);
  });
});
