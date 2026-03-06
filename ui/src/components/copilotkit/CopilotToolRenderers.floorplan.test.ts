import { describe, expect, it } from "vitest";

import { buildFloorPlanSnapshot } from "@/lib/floorPlanPreviewParser";

describe("buildFloorPlanSnapshot", () => {
  it("returns typed scene and scene summary for valid render payload", () => {
    const snapshot = buildFloorPlanSnapshot("complete", {
      caption: "Draft",
      images: [
        {
          attachment_id: "svg-1",
          mime_type: "image/svg+xml",
          uri: "/attachments/svg-1",
          width: null,
          height: null,
        },
      ],
      scene_revision: 2,
      scene_level: "detailed",
      legend_items: ["Walls"],
      warnings: [],
      scene: {
        scene_level: "detailed",
        architecture: {
          dimensions_cm: { length_x_cm: 400, depth_y_cm: 300, height_z_cm: 240 },
          walls: [
            {
              wall_id: "w1",
              start_cm: { x_cm: 0, y_cm: 0 },
              end_cm: { x_cm: 400, y_cm: 0 },
            },
          ],
        },
      },
      scene_summary: {
        wall_count: 4,
        door_count: 1,
        window_count: 1,
        placement_count: 2,
        fixture_count: 1,
        tagged_item_count: 0,
        has_outline: true,
      },
    });

    expect(snapshot).not.toBeNull();
    expect(snapshot?.scene?.scene_level).toBe("detailed");
    expect(snapshot?.sceneSummary?.wall_count).toBe(4);
  });

  it("drops invalid scene payloads and keeps 2D metadata intact", () => {
    const snapshot = buildFloorPlanSnapshot("complete", {
      caption: "Draft",
      images: [
        {
          attachment_id: "svg-1",
          mime_type: "image/svg+xml",
          uri: "/attachments/svg-1",
          width: null,
          height: null,
        },
      ],
      scene_revision: 2,
      scene_level: "detailed",
      scene: { invalid: true },
      scene_summary: { also: "invalid" },
    });

    expect(snapshot).not.toBeNull();
    expect(snapshot?.scene).toBeNull();
    expect(snapshot?.sceneSummary).toBeNull();
    expect(snapshot?.sceneRevision).toBe(2);
  });
});
