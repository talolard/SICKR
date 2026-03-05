import { render, screen } from "@testing-library/react";

import { RoomPhotoAnalysisToolRenderer } from "./RoomPhotoAnalysisToolRenderer";

describe("RoomPhotoAnalysisToolRenderer", () => {
  it("renders room hints", () => {
    render(
      <RoomPhotoAnalysisToolRenderer
        result={{
          caption: "Room analysis complete",
          images: [],
          room_hints: ["Detected objects include: table, chair."],
        }}
      />,
    );

    expect(screen.getByTestId("room-photo-analysis-output")).toBeInTheDocument();
    expect(screen.getByTestId("room-hints-list")).toBeInTheDocument();
    expect(screen.getByText(/table, chair/)).toBeInTheDocument();
  });

  it("renders no-hints state", () => {
    render(
      <RoomPhotoAnalysisToolRenderer
        result={{
          caption: "Room analysis complete",
          images: [],
          room_hints: [],
        }}
      />,
    );

    expect(screen.getByText("No room hints returned.")).toBeInTheDocument();
  });
});
