import { render, screen } from "@testing-library/react";

import { RoomDetailDetailsFromPhotoToolRenderer } from "./RoomDetailDetailsFromPhotoToolRenderer";

describe("RoomDetailDetailsFromPhotoToolRenderer", () => {
  it("renders grouped room details", () => {
    render(
      <RoomDetailDetailsFromPhotoToolRenderer
        result={{
          caption: "Room detail analysis complete.",
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
              notes: ["Wide shot"],
            },
          ],
          notes: ["Pet-visible living room."],
        }}
      />,
    );

    expect(screen.getByTestId("room-detail-details-output")).toBeInTheDocument();
    expect(screen.getByText("living room (high)")).toBeInTheDocument();
    expect(screen.getByText("same room likely")).toBeInTheDocument();
    expect(screen.getByText("sofa")).toBeInTheDocument();
    expect(screen.getByText("Legos")).toBeInTheDocument();
    expect(screen.getByTestId("room-detail-image-assessments")).toBeInTheDocument();
    expect(screen.getByTestId("room-detail-notes")).toBeInTheDocument();
  });

  it("renders empty states for missing grouped details", () => {
    render(
      <RoomDetailDetailsFromPhotoToolRenderer
        result={{
          caption: "Room detail analysis complete.",
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
          image_assessments: [],
          notes: [],
        }}
      />,
    );

    expect(screen.getByText("Uncertain whether all images show rooms.")).toBeInTheDocument();
    expect(screen.getByText("Non-room images: Image 2")).toBeInTheDocument();
    expect(screen.getAllByText("None reported.")).toHaveLength(4);
    expect(screen.getByText("No per-image assessments returned.")).toBeInTheDocument();
    expect(screen.getByText("No extra notes returned.")).toBeInTheDocument();
  });
});
