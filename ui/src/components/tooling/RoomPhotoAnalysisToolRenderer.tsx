import type { ReactElement } from "react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";
import type { AttachmentRef } from "../../lib/attachments";

export type RoomPhotoAnalysisToolResult = {
  caption: string;
  images: AttachmentRef[];
  room_hints: string[];
};

type RoomPhotoAnalysisToolRendererProps = {
  result: RoomPhotoAnalysisToolResult;
};

export function RoomPhotoAnalysisToolRenderer(
  props: RoomPhotoAnalysisToolRendererProps,
): ReactElement {
  const { result } = props;
  return (
    <section className="rounded border bg-white p-2" data-testid="room-photo-analysis-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <div className="mt-2">
        <p className="text-sm font-medium">Room hints</p>
        {result.room_hints.length > 0 ? (
          <ul className="mt-1 space-y-1 text-sm" data-testid="room-hints-list">
            {result.room_hints.map((hint, index) => (
              <li className="rounded border px-2 py-1" key={`${hint}-${index}`}>
                {hint}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-600">No room hints returned.</p>
        )}
      </div>
    </section>
  );
}
