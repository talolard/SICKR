import type { ReactElement } from "react";

export type RoomPhotoImageAssessment = {
  image_index: number;
  appears_to_show_room: boolean | null;
  room_type: string;
  confidence: string;
  notes: string[];
};

export type RoomDetailObjectsOfInterest = {
  major_furniture: string[];
  fixtures: string[];
  lifestyle_indicators: string[];
  other_items: string[];
};

export type RoomDetailDetailsFromPhotoToolResult = {
  caption: string;
  room_type: string;
  confidence: string;
  all_images_appear_to_show_rooms: boolean | null;
  non_room_image_indices: number[];
  cross_image_room_relationship: string;
  objects_of_interest: RoomDetailObjectsOfInterest;
  image_assessments: RoomPhotoImageAssessment[];
  notes: string[];
};

type RoomDetailDetailsFromPhotoToolRendererProps = {
  result: RoomDetailDetailsFromPhotoToolResult;
};

const objectSections: Array<{
  key: keyof RoomDetailObjectsOfInterest;
  title: string;
}> = [
  { key: "major_furniture", title: "Major furniture" },
  { key: "fixtures", title: "Fixtures" },
  { key: "lifestyle_indicators", title: "Lifestyle indicators" },
  { key: "other_items", title: "Other items" },
];

function humanizeLabel(value: string): string {
  return value.replaceAll("_", " ");
}

export function RoomDetailDetailsFromPhotoToolRenderer(
  props: RoomDetailDetailsFromPhotoToolRendererProps,
): ReactElement {
  const { result } = props;
  return (
    <section
      className="rounded border bg-white p-3"
      data-testid="room-detail-details-output"
    >
      <p className="text-sm text-gray-800">{result.caption}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded border px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-gray-500">Room type</p>
          <p className="text-sm font-medium">
            {humanizeLabel(result.room_type)} ({result.confidence})
          </p>
        </div>
        <div className="rounded border px-3 py-2">
          <p className="text-xs uppercase tracking-wide text-gray-500">Image relationship</p>
          <p className="text-sm font-medium">
            {humanizeLabel(result.cross_image_room_relationship)}
          </p>
        </div>
      </div>

      <div className="mt-3 rounded border px-3 py-2">
        <p className="text-xs uppercase tracking-wide text-gray-500">Room coverage</p>
        <p className="text-sm">
          {result.all_images_appear_to_show_rooms === null
            ? "Uncertain whether all images show rooms."
            : result.all_images_appear_to_show_rooms
              ? "All images appear to show rooms."
              : "Some images may not show rooms."}
        </p>
        {result.non_room_image_indices.length > 0 ? (
          <p className="mt-1 text-sm text-amber-700">
            Non-room images:{" "}
            {result.non_room_image_indices.map((index) => `Image ${index + 1}`).join(", ")}
          </p>
        ) : null}
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2" data-testid="room-detail-object-groups">
        {objectSections.map((section) => {
          const values = result.objects_of_interest[section.key];
          return (
            <div className="rounded border px-3 py-2" key={section.key}>
              <p className="text-sm font-medium">{section.title}</p>
              {values.length > 0 ? (
                <ul className="mt-1 space-y-1 text-sm">
                  {values.map((value) => (
                    <li className="rounded border px-2 py-1" key={`${section.key}-${value}`}>
                      {value}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-sm text-gray-600">None reported.</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-3">
        <p className="text-sm font-medium">Per-image assessment</p>
        {result.image_assessments.length > 0 ? (
          <ul className="mt-1 space-y-2 text-sm" data-testid="room-detail-image-assessments">
            {result.image_assessments.map((assessment) => (
              <li className="rounded border px-3 py-2" key={`image-${assessment.image_index}`}>
                <p className="font-medium">
                  Image {assessment.image_index + 1}: {humanizeLabel(assessment.room_type)} (
                  {assessment.confidence})
                </p>
                <p className="text-gray-700">
                  {assessment.appears_to_show_room === null
                    ? "Uncertain whether this image shows a room."
                    : assessment.appears_to_show_room
                      ? "Appears to show a room."
                      : "May not show a room."}
                </p>
                {assessment.notes.length > 0 ? (
                  <ul className="mt-1 space-y-1 text-gray-700">
                    {assessment.notes.map((note) => (
                      <li key={`image-${assessment.image_index}-${note}`}>{note}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-gray-600">No per-image assessments returned.</p>
        )}
      </div>

      <div className="mt-3">
        <p className="text-sm font-medium">Notes</p>
        {result.notes.length > 0 ? (
          <ul className="mt-1 space-y-1 text-sm" data-testid="room-detail-notes">
            {result.notes.map((note) => (
              <li className="rounded border px-2 py-1" key={note}>
                {note}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-gray-600">No extra notes returned.</p>
        )}
      </div>
    </section>
  );
}
