import type { ReactElement } from "react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";
import type { AttachmentRef } from "../../lib/attachments";

export type DetectedObject = {
  label: string;
  bbox_xyxy_px: [number, number, number, number];
  bbox_xyxy_norm: [number, number, number, number];
};

export type ObjectDetectionToolResult = {
  caption: string;
  images: AttachmentRef[];
  detections: DetectedObject[];
};

type ObjectDetectionToolRendererProps = {
  result: ObjectDetectionToolResult;
};

export function ObjectDetectionToolRenderer(
  props: ObjectDetectionToolRendererProps,
): ReactElement {
  const { result } = props;
  return (
    <section className="space-y-3" data-testid="object-detection-tool-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <div className="rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4">
        <p className="editorial-eyebrow">Detected objects</p>
        <p className="mt-2 text-sm font-semibold text-primary">
          {result.detections.length} detected object{result.detections.length === 1 ? "" : "s"}
        </p>
        {result.detections.length > 0 ? (
          <ul className="mt-3 space-y-2 text-sm" data-testid="object-detection-list">
            {result.detections.map((detection, index) => (
              <li
                className="rounded-[18px] bg-[color:var(--surface-container-lowest)] px-3 py-2 text-on-surface"
                key={`${detection.label}-${index}`}
              >
                {detection.label} [{detection.bbox_xyxy_px.join(", ")}]
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-on-surface-variant">No confident objects detected.</p>
        )}
      </div>
    </section>
  );
}
