import { z } from "zod";

export const floorPlanSceneSummarySchema = z.object({
  wall_count: z.number(),
  door_count: z.number(),
  window_count: z.number(),
  placement_count: z.number(),
  fixture_count: z.number(),
  tagged_item_count: z.number(),
  has_outline: z.boolean(),
});

export const floorPlanSceneSchema = z.object({
  scene_level: z.enum(["baseline", "detailed"]),
  architecture: z.object({
    dimensions_cm: z.object({
      length_x_cm: z.number(),
      depth_y_cm: z.number(),
      height_z_cm: z.number(),
    }),
    walls: z.array(
      z.object({
        wall_id: z.string(),
        start_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
        end_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
        thickness_cm: z.number().optional(),
        color: z.string().nullable().optional(),
        label: z.string().nullable().optional(),
      }),
    ),
    doors: z
      .array(
        z.object({
          opening_id: z.string(),
          start_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
          end_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
          opens_towards: z.string().nullable().optional(),
          panel_length_cm: z.number().nullable().optional(),
          label: z.string().nullable().optional(),
        }),
      )
      .optional(),
    windows: z
      .array(
        z.object({
          opening_id: z.string(),
          start_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
          end_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
          z_min_cm: z.number().nullable().optional(),
          z_max_cm: z.number().nullable().optional(),
          panel_count: z.number().optional(),
          frame_cm: z.number().optional(),
          label: z.string().nullable().optional(),
        }),
      )
      .optional(),
  }),
  placements: z
    .array(
      z.object({
        placement_id: z.string(),
        name: z.string(),
        kind: z.string().optional(),
        position_cm: z.object({ x_cm: z.number(), y_cm: z.number() }),
        size_cm: z.object({ x_cm: z.number(), y_cm: z.number(), z_cm: z.number() }),
        z_cm: z.number().optional(),
        color: z.string().nullable().optional(),
        wall_mounted: z.boolean().optional(),
        stacked_on_placement_id: z.string().nullable().optional(),
        label: z.string().nullable().optional(),
        notes: z.string().nullable().optional(),
      }),
    )
    .optional(),
  fixtures: z
    .array(
      z.discriminatedUnion("fixture_kind", [
        z.object({
          fixture_kind: z.literal("socket"),
          fixture_id: z.string(),
          x_cm: z.number(),
          y_cm: z.number(),
          z_cm: z.number().optional(),
          label: z.string().nullable().optional(),
        }),
        z.object({
          fixture_kind: z.literal("light"),
          fixture_id: z.string(),
          x_cm: z.number(),
          y_cm: z.number(),
          z_cm: z.number().optional(),
          label: z.string().nullable().optional(),
        }),
      ]),
    )
    .optional(),
  tagged_items: z.array(z.unknown()).optional(),
});

export type FloorPlanScene = z.infer<typeof floorPlanSceneSchema>;
export type FloorPlanSceneSummary = z.infer<typeof floorPlanSceneSummarySchema>;
