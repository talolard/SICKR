import { render, screen } from "@testing-library/react";

import { SegmentationToolRenderer } from "./SegmentationToolRenderer";

describe("SegmentationToolRenderer", () => {
  it("renders segmentation masks", () => {
    render(
      <SegmentationToolRenderer
        result={{
          caption: "Segmentation done",
          images: [],
          prompt: "clutter",
          masks: [
            {
              label: "mask-1",
              mask_image: {
                attachment_id: "mask-1",
                mime_type: "image/png",
                uri: "/attachments/mask-1",
                width: 400,
                height: 300,
                file_name: "mask-1.png",
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("segmentation-tool-output")).toBeInTheDocument();
    expect(screen.getByTestId("segmentation-mask-list")).toBeInTheDocument();
    expect(screen.getByText("mask-1")).toBeInTheDocument();
  });

  it("renders empty mask state", () => {
    render(
      <SegmentationToolRenderer
        result={{
          caption: "Segmentation done",
          images: [],
          prompt: "clutter",
          masks: [],
        }}
      />,
    );

    expect(screen.getByText("No masks returned.")).toBeInTheDocument();
  });
});
