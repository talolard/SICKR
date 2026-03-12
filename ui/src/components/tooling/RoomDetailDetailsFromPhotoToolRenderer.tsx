import type { ReactElement } from "react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";
import type { AttachmentRef } from "../../lib/attachments";

export type RoomDetailDetailsFromPhotoToolResult = {
  caption: string;
  images: AttachmentRef[];
  room_type: string;
  confidence: string;
  all_images_appear_to_show_rooms: boolean | null;
  non_room_image_indices: number[];
  cross_image_room_relationship: string;
  objects_of_interest: {
    major_furniture: string[];
    fixtures: string[];
    lifestyle_indicators: string[];
    other_items: string[];
  };
  image_assessments: Array<{
    image_index: number;
    appears_to_show_room: boolean | null;
    room_type: string;
    confidence: string;
    notes: string[];
  }>;
  notes: string[];
};

type RoomDetailDetailsFromPhotoToolRendererProps = {
  result: RoomDetailDetailsFromPhotoToolResult;
};

export function RoomDetailDetailsFromPhotoToolRenderer(
  props: RoomDetailDetailsFromPhotoToolRendererProps,
): ReactElement {
  const { result } = props;
  return (
    <section
      className="rounded border bg-white p-3"
      data-testid="room-detail-details-from-photo-output"
    >
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <div className="mt-3 space-y-3">
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <div className="rounded border px-2 py-2">
            <p className="font-medium">Inferred room type</p>
            <p>{`${result.room_type} (${result.confidence})`}</p>
          </div>
          <div className="rounded border px-2 py-2">
            <p className="font-medium">Cross-image relationship</p>
            <p>{result.cross_image_room_relationship}</p>
          </div>
        </div>

        {result.non_room_image_indices.length > 0 ? (
          <p className="rounded border border-amber-300 bg-amber-50 px-2 py-2 text-sm">
            Non-room images detected at indices: {result.non_room_image_indices.join(", ")}
          </p>
        ) : null}

        <ObjectGroup
          title="Major furniture"
          items={result.objects_of_interest.major_furniture}
          testId="room-detail-major-furniture"
          emptyText="No major furniture recorded."
        />
        <ObjectGroup
          title="Fixtures"
          items={result.objects_of_interest.fixtures}
          testId="room-detail-fixtures"
          emptyText="No fixtures recorded."
        />
        <ObjectGroup
          title="Lifestyle indicators"
          items={result.objects_of_interest.lifestyle_indicators}
          testId="room-detail-lifestyle-indicators"
          emptyText="No lifestyle indicators recorded."
        />
        <ObjectGroup
          title="Other items"
          items={result.objects_of_interest.other_items}
          testId="room-detail-other-items"
          emptyText="No other items recorded."
        />

        <div>
          <p className="text-sm font-medium">Per-image assessments</p>
          <ul className="mt-1 space-y-2" data-testid="room-detail-image-assessments">
            {result.image_assessments.map((assessment) => (
              <li className="rounded border px-2 py-2 text-sm" key={assessment.image_index}>
                <p className="font-medium">{`Image ${assessment.image_index}`}</p>
                <p>
                  {`shows room: ${
                    assessment.appears_to_show_room === null
                      ? "unknown"
                      : assessment.appears_to_show_room
                        ? "yes"
                        : "no"
                  }`}
                </p>
                <p>{`room type: ${assessment.room_type} (${assessment.confidence})`}</p>
                {assessment.notes.length > 0 ? (
                  <ul className="mt-1 space-y-1">
                    {assessment.notes.map((note) => (
                      <li key={`${assessment.image_index}-${note}`}>{note}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </div>

        {result.notes.length > 0 ? (
          <div>
            <p className="text-sm font-medium">Notes</p>
            <ul className="mt-1 space-y-1 text-sm" data-testid="room-detail-notes">
              {result.notes.map((note) => (
                <li className="rounded border px-2 py-1" key={note}>
                  {note}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  );
}

type ObjectGroupProps = {
  title: string;
  items: string[];
  testId: string;
  emptyText: string;
};

function ObjectGroup(props: ObjectGroupProps): ReactElement {
  const { title, items, testId, emptyText } = props;
  return (
    <div>
      <p className="text-sm font-medium">{title}</p>
      {items.length > 0 ? (
        <ul className="mt-1 flex flex-wrap gap-2 text-sm" data-testid={testId}>
          {items.map((item) => (
            <li className="rounded border px-2 py-1" key={item}>
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-600">{emptyText}</p>
      )}
    </div>
  );
}
