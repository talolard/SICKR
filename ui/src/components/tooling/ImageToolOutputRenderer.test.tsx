import { fireEvent, render, screen } from "@testing-library/react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";

describe("ImageToolOutputRenderer", () => {
  it("opens and closes the image viewer modal", () => {
    render(
      <ImageToolOutputRenderer
        caption="Draft floor plan"
        images={[
          {
            attachment_id: "generated-1",
            mime_type: "image/svg+xml",
            uri: "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E",
            width: 640,
            height: 420,
            file_name: "floor-plan.svg",
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId("image-thumb-generated-1"));
    expect(screen.getByTestId("image-viewer-modal")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByTestId("image-viewer-modal")).not.toBeInTheDocument();
  });
});
