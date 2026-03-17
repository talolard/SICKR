import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { BundleProposalBridge, FloorPlanRenderBridge } from "./bridges";

const { publishFloorPlanRendered } = vi.hoisted(() => ({
  publishFloorPlanRendered: vi.fn(),
}));

vi.mock("@/lib/floorPlanPreviewEvents", () => ({
  publishFloorPlanRendered,
}));

describe("BundleProposalBridge", () => {
  it("publishes completed bundle proposals to the caller", async () => {
    const onBundleProposed = vi.fn();

    render(
      <BundleProposalBridge
        status="complete"
        result={{
          bundle_id: "bundle-1",
          title: "Starter bundle",
          notes: null,
          budget_cap_eur: 250,
          items: [
            {
              item_id: "sku-1",
              product_name: "PAX",
              description_text: "Wardrobe",
              price_eur: 199,
              quantity: 1,
              line_total_eur: 199,
              reason: "Primary storage",
            },
          ],
          bundle_total_eur: 199,
          validations: [],
          created_at: "2026-03-12T00:00:00Z",
          run_id: "run-1",
        }}
        onBundleProposed={onBundleProposed}
      />,
    );

    await waitFor(() => {
      expect(onBundleProposed).toHaveBeenCalledWith(
        expect.objectContaining({
          bundle_id: "bundle-1",
          title: "Starter bundle",
        }),
      );
    });
    expect(screen.getByText("Saved to bundles panel")).toBeInTheDocument();
  });
});

describe("FloorPlanRenderBridge", () => {
  it("publishes floor-plan snapshots and renders preview output", async () => {
    const onFloorPlanRendered = vi.fn();

    render(
      <FloorPlanRenderBridge
        status="complete"
        result={{
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
          warnings: [],
          legend_items: ["Walls"],
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
        }}
        onFloorPlanRendered={onFloorPlanRendered}
      />,
    );

    await waitFor(() => {
      expect(onFloorPlanRendered).toHaveBeenCalledWith(
        expect.objectContaining({
          caption: "Draft",
          sceneLevel: "detailed",
          sceneRevision: 2,
        }),
      );
    });
    expect(publishFloorPlanRendered).toHaveBeenCalled();
    expect(screen.getByTestId("image-tool-output")).toBeInTheDocument();
  });
});
