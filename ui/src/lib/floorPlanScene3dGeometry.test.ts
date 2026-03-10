import { describe, expect, it } from "vitest";

import type { FloorPlanScene } from "@/lib/floorPlanScene";
import { toSceneGeometry } from "@/lib/floorPlanScene3dGeometry";

function buildScene(overrides?: Partial<FloorPlanScene["architecture"]>): FloorPlanScene {
  return {
    scene_level: "detailed",
    architecture: {
      dimensions_cm: {
        length_x_cm: 400,
        depth_y_cm: 300,
        height_z_cm: 250,
      },
      walls: [
        {
          wall_id: "bottom",
          start_cm: { x_cm: 0, y_cm: 0 },
          end_cm: { x_cm: 400, y_cm: 0 },
          thickness_cm: 10,
          color: null,
          label: null,
        },
        {
          wall_id: "right",
          start_cm: { x_cm: 400, y_cm: 0 },
          end_cm: { x_cm: 400, y_cm: 300 },
          thickness_cm: 10,
          color: null,
          label: null,
        },
        {
          wall_id: "top",
          start_cm: { x_cm: 400, y_cm: 300 },
          end_cm: { x_cm: 0, y_cm: 300 },
          thickness_cm: 10,
          color: null,
          label: null,
        },
        {
          wall_id: "left",
          start_cm: { x_cm: 0, y_cm: 300 },
          end_cm: { x_cm: 0, y_cm: 0 },
          thickness_cm: 10,
          color: null,
          label: null,
        },
      ],
      doors: [
        {
          opening_id: "door-1",
          start_cm: { x_cm: 0, y_cm: 30 },
          end_cm: { x_cm: 0, y_cm: 100 },
          z_min_cm: null,
          z_max_cm: null,
          opens_towards: null,
          panel_length_cm: null,
          label: null,
        },
      ],
      windows: [
        {
          opening_id: "window-1",
          start_cm: { x_cm: 400, y_cm: 100 },
          end_cm: { x_cm: 400, y_cm: 200 },
          z_min_cm: 80,
          z_max_cm: 200,
          panel_count: 1,
          frame_cm: 0,
          label: null,
        },
      ],
      ...overrides,
    },
    placements: [],
    fixtures: [],
    tagged_items: [],
  };
}

describe("toSceneGeometry", () => {
  it("assigns doors and windows to their wall cutouts", () => {
    const geometry = toSceneGeometry(buildScene());

    const leftWall = geometry.walls.find((wall) => wall.id === "left");
    const rightWall = geometry.walls.find((wall) => wall.id === "right");

    expect(leftWall).toBeDefined();
    expect(rightWall).toBeDefined();
    expect(leftWall?.openings).toHaveLength(1);
    expect(rightWall?.openings).toHaveLength(1);
    expect(geometry.openingInserts).toHaveLength(2);

    const doorInsert = geometry.openingInserts.find((opening) => opening.id === "door-1");
    const windowInsert = geometry.openingInserts.find((opening) => opening.id === "window-1");

    expect(doorInsert?.kind).toBe("door");
    expect(windowInsert?.kind).toBe("window");
  });

  it("uses default door height when z-range is omitted", () => {
    const geometry = toSceneGeometry(buildScene());
    const doorInsert = geometry.openingInserts.find((opening) => opening.id === "door-1");

    expect(doorInsert).toBeDefined();
    // room height 2.5m -> min(2.1, 2.5 * 0.82) = 2.05m
    expect(doorInsert?.heightM).toBeCloseTo(2.05, 3);
    expect(doorInsert?.center[1]).toBeCloseTo(1.025, 3);
  });

  it("honors explicit door z-range when provided", () => {
    const scene = buildScene({
      doors: [
        {
          opening_id: "door-1",
          start_cm: { x_cm: 0, y_cm: 30 },
          end_cm: { x_cm: 0, y_cm: 100 },
          z_min_cm: 10,
          z_max_cm: 220,
          opens_towards: null,
          panel_length_cm: null,
          label: null,
        },
      ],
    });

    const geometry = toSceneGeometry(scene);
    const doorInsert = geometry.openingInserts.find((opening) => opening.id === "door-1");

    expect(doorInsert).toBeDefined();
    expect(doorInsert?.heightM).toBeCloseTo(2.1, 3);
    expect(doorInsert?.center[1]).toBeCloseTo(1.15, 3);
  });

  it("drops overlapping openings on the same wall deterministically", () => {
    const scene = buildScene({
      doors: [
        {
          opening_id: "door-1",
          start_cm: { x_cm: 0, y_cm: 30 },
          end_cm: { x_cm: 0, y_cm: 120 },
          z_min_cm: 0,
          z_max_cm: 210,
          opens_towards: null,
          panel_length_cm: null,
          label: null,
        },
        {
          opening_id: "door-2",
          start_cm: { x_cm: 0, y_cm: 90 },
          end_cm: { x_cm: 0, y_cm: 150 },
          z_min_cm: 0,
          z_max_cm: 210,
          opens_towards: null,
          panel_length_cm: null,
          label: null,
        },
      ],
      windows: [],
    });

    const geometry = toSceneGeometry(scene);

    expect(geometry.openingInserts).toHaveLength(1);
    expect(geometry.openingInserts[0]?.id).toBe("door-1");
  });
});
