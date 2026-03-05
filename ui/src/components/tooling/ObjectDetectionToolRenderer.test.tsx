import { render, screen } from "@testing-library/react";

import { ObjectDetectionToolRenderer } from "./ObjectDetectionToolRenderer";

describe("ObjectDetectionToolRenderer", () => {
  it("renders detections and image output", () => {
    render(
      <ObjectDetectionToolRenderer
        result={{
          caption: "Detected items",
          images: [
            {
              attachment_id: "det-overlay",
              mime_type: "image/png",
              uri: "/attachments/det-overlay",
              width: 400,
              height: 300,
              file_name: "overlay.png",
            },
          ],
          detections: [
            {
              label: "chair",
              bbox_xyxy_px: [10, 20, 140, 220],
              bbox_xyxy_norm: [0.025, 0.067, 0.35, 0.733],
            },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("object-detection-tool-output")).toBeInTheDocument();
    expect(screen.getByTestId("object-detection-list")).toBeInTheDocument();
    expect(screen.getByText(/chair/)).toBeInTheDocument();
  });

  it("renders empty-state text", () => {
    render(
      <ObjectDetectionToolRenderer
        result={{
          caption: "Detected items",
          images: [],
          detections: [],
        }}
      />,
    );

    expect(screen.getByText("No confident objects detected.")).toBeInTheDocument();
  });
});
