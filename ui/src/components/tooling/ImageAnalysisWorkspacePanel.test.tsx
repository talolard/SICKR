import { fireEvent, render, screen } from "@testing-library/react";

import { ImageAnalysisWorkspacePanel } from "./ImageAnalysisWorkspacePanel";

describe("ImageAnalysisWorkspacePanel", () => {
  it("renders the empty photo-board state", () => {
    render(<ImageAnalysisWorkspacePanel attachments={[]} />);

    expect(screen.getByTestId("image-analysis-workspace-panel")).toBeInTheDocument();
    expect(screen.getByText("Visual context")).toBeInTheDocument();
    expect(screen.getByText(/Upload room photos/i)).toBeInTheDocument();
  });

  it("opens and closes the modal for uploaded images", () => {
    render(
      <ImageAnalysisWorkspacePanel
        attachments={[
          {
            attachment_id: "img-1",
            mime_type: "image/png",
            uri: "/attachments/img-1",
            width: 1200,
            height: 900,
            file_name: "living-room.png",
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByTestId("image-analysis-hero-img-1"));
    expect(screen.getByTestId("image-analysis-viewer-modal")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByTestId("image-analysis-viewer-modal")).not.toBeInTheDocument();
  });
});
