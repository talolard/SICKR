import { render, screen } from "@testing-library/react";

import { RoomDetailDetailsFromPhotoToolRenderer } from "./RoomDetailDetailsFromPhotoToolRenderer";

describe("RoomDetailDetailsFromPhotoToolRenderer", () => {
  it("renders grouped objects and per-image assessments", () => {
    render(
      <RoomDetailDetailsFromPhotoToolRenderer
        result={{
          caption: "Room detail analysis complete.",
          images: [],
          room_type: "living_room",
          confidence: "high",
          all_images_appear_to_show_rooms: true,
          non_room_image_indices: [],
          cross_image_room_relationship: "same_room_likely",
          objects_of_interest: {
            major_furniture: ["sofa", "coffee table"],
            fixtures: ["radiator"],
            lifestyle_indicators: ["cat", "Legos"],
            other_items: ["rug"],
          },
          image_assessments: [
            {
              image_index: 0,
              appears_to_show_room: true,
              room_type: "living_room",
              confidence: "high",
              notes: ["Large sectional visible."],
            },
          ],
          notes: ["Images likely show the same room."],
        }}
      />,
    );

    expect(
      screen.getByTestId("room-detail-details-from-photo-output"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("room-detail-major-furniture")).toBeInTheDocument();
    expect(screen.getByText("sofa")).toBeInTheDocument();
    expect(screen.getByText("cat")).toBeInTheDocument();
    expect(screen.getByTestId("room-detail-image-assessments")).toBeInTheDocument();
    expect(screen.getByText("Large sectional visible.")).toBeInTheDocument();
    expect(screen.getByTestId("room-detail-notes")).toBeInTheDocument();
  });

  it("renders empty states for missing grouped items", () => {
    render(
      <RoomDetailDetailsFromPhotoToolRenderer
        result={{
          caption: "Room detail analysis complete.",
          images: [],
          room_type: "unknown",
          confidence: "low",
          all_images_appear_to_show_rooms: null,
          non_room_image_indices: [1],
          cross_image_room_relationship: "uncertain",
          objects_of_interest: {
            major_furniture: [],
            fixtures: [],
            lifestyle_indicators: [],
            other_items: [],
          },
          image_assessments: [
            {
              image_index: 0,
              appears_to_show_room: null,
              room_type: "unknown",
              confidence: "low",
              notes: [],
            },
          ],
          notes: [],
        }}
      />,
    );

    expect(screen.getByText("No major furniture recorded.")).toBeInTheDocument();
    expect(screen.getByText("No fixtures recorded.")).toBeInTheDocument();
    expect(
      screen.getByText("Non-room images detected at indices: 1"),
    ).toBeInTheDocument();
  });
});
