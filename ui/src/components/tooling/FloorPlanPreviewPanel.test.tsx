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
