import { fireEvent, render, screen } from "@testing-library/react";

import { FloorPlanPreviewPanel } from "./FloorPlanPreviewPanel";

describe("FloorPlanPreviewPanel", () => {
  it("renders empty state", () => {
    render(<FloorPlanPreviewPanel preview={null} />);

    expect(screen.getByText("Floor Plan Preview")).toBeInTheDocument();
    expect(screen.getByText(/Render a floor plan/i)).toBeInTheDocument();
  });

  it("renders preview metadata and image", () => {
    render(
      <FloorPlanPreviewPanel
        preview={{
          threadId: "thread-1",
          caption: "Latest layout",
          sceneRevision: 4,
          sceneLevel: "detailed",
          warnings: [
            {
              severity: "warn",
              code: "placement_out_of_bounds_x",
              message: "Placement extends beyond room x-length.",
            },
          ],
          legendItems: ["Walls"],
          scene: {
            scene_level: "detailed",
            architecture: {
              dimensions_cm: { length_x_cm: 400, depth_y_cm: 300, height_z_cm: 250 },
              walls: [
                {
                  wall_id: "w1",
                  start_cm: { x_cm: 0, y_cm: 0 },
                  end_cm: { x_cm: 400, y_cm: 0 },
                },
              ],
            },
            fixtures: [
              {
                fixture_kind: "light",
                fixture_id: "light-1",
                x_cm: 120,
                y_cm: 80,
                z_cm: 220,
              },
            ],
          },
          sceneSummary: {
            wall_count: 4,
            door_count: 1,
            window_count: 1,
            placement_count: 1,
            fixture_count: 1,
            tagged_item_count: 0,
            has_outline: true,
          },
          images: [
            {
              attachment_id: "svg-1",
              mime_type: "image/svg+xml",
              uri: "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
              width: 640,
              height: 420,
              file_name: "floor.svg",
            },
          ],
        }}
      />,
    );

    expect(screen.getByText(/Revision 4/i)).toBeInTheDocument();
    expect(screen.getByText("Latest layout")).toBeInTheDocument();
    expect(screen.getByAltText("Latest floor plan")).toBeInTheDocument();
    expect(screen.getByText(/placement_out_of_bounds_x/i)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "2D" })).toHaveAttribute("aria-selected", "true");
  });

  it("switches to 3d tab and shows lighting emphasis metadata", () => {
    render(
      <FloorPlanPreviewPanel
        preview={{
          threadId: "thread-3d",
          caption: "3D layout",
          sceneRevision: 6,
          sceneLevel: "detailed",
          warnings: [],
          legendItems: [],
          scene: {
            scene_level: "detailed",
            architecture: {
              dimensions_cm: { length_x_cm: 420, depth_y_cm: 320, height_z_cm: 260 },
              walls: [
                {
                  wall_id: "w1",
                  start_cm: { x_cm: 0, y_cm: 0 },
                  end_cm: { x_cm: 420, y_cm: 0 },
                },
              ],
            },
            fixtures: [
              {
                fixture_kind: "light",
                fixture_id: "light-2",
                x_cm: 100,
                y_cm: 100,
                z_cm: 220,
              },
            ],
          },
          sceneSummary: {
            wall_count: 4,
            door_count: 0,
            window_count: 0,
            placement_count: 0,
            fixture_count: 1,
            tagged_item_count: 0,
            has_outline: false,
          },
          images: [
            {
              attachment_id: "svg-3",
              mime_type: "image/svg+xml",
              uri: "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
              width: 640,
              height: 420,
              file_name: "floor.svg",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "3D" }));
    expect(screen.getByRole("tab", { name: "3D" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("lighting-emphasis-caption")).toHaveTextContent(
      /Lighting emphasis markers: 1 fixture highlighted/i,
    );
  });

  it("shows 3d empty-state when scene payload is unavailable", () => {
    render(
      <FloorPlanPreviewPanel
        preview={{
          threadId: "thread-no-scene",
          caption: "2D-only layout",
          sceneRevision: 7,
          sceneLevel: "baseline",
          warnings: [],
          legendItems: [],
          scene: null,
          sceneSummary: null,
          images: [
            {
              attachment_id: "svg-4",
              mime_type: "image/svg+xml",
              uri: "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
              width: 640,
              height: 420,
              file_name: "floor.svg",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "3D" }));
    expect(screen.getByTestId("floor-plan-3d-empty")).toBeInTheDocument();
  });

  it("closes modal when backdrop is clicked", () => {
    render(
      <FloorPlanPreviewPanel
        preview={{
          threadId: "thread-2",
          caption: "Latest layout",
          sceneRevision: 5,
          sceneLevel: "detailed",
          warnings: [],
          legendItems: [],
          scene: null,
          sceneSummary: null,
          images: [
            {
              attachment_id: "svg-2",
              mime_type: "image/svg+xml",
              uri: "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
              width: 640,
              height: 420,
              file_name: "floor.svg",
            },
          ],
        }}
      />,
    );

    fireEvent.click(screen.getByText("Open large view"));
    expect(screen.getByAltText("Floor plan full view")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("floor-plan-backdrop"));
    expect(screen.queryByAltText("Floor plan full view")).not.toBeInTheDocument();
  });
});
