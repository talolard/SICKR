import { render, screen } from "@testing-library/react";

import { DepthEstimationToolRenderer } from "./DepthEstimationToolRenderer";

describe("DepthEstimationToolRenderer", () => {
  it("renders depth params and images", () => {
    render(
      <DepthEstimationToolRenderer
        result={{
          caption: "Depth done",
          images: [
            {
              attachment_id: "depth-1",
              mime_type: "image/png",
              uri: "/attachments/depth-1",
              width: 400,
              height: 300,
              file_name: "depth.png",
            },
          ],
          parameters_used: {
            ensemble_size: 10,
            processing_res: 768,
            resample_method: "bilinear",
            seed: 42,
            output_format: "png",
          },
        }}
      />,
    );

    expect(screen.getByTestId("depth-estimation-tool-output")).toBeInTheDocument();
    expect(screen.getByText(/ensemble 10/)).toBeInTheDocument();
  });
});
