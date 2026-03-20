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
    <section className="space-y-3" data-testid="room-photo-analysis-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <div className="rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4">
        <p className="editorial-eyebrow">Room hints</p>
        {result.room_hints.length > 0 ? (
          <ul className="mt-3 flex flex-wrap gap-2 text-sm" data-testid="room-hints-list">
            {result.room_hints.map((hint, index) => (
              <li
                className="rounded-full bg-[color:var(--surface-container-lowest)] px-3 py-1.5 text-on-surface"
                key={`${hint}-${index}`}
              >
                {hint}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-on-surface-variant">No room hints returned.</p>
        )}
      </div>
    </section>
  );
}
