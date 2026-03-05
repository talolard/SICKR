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
    <section className="rounded border bg-white p-2" data-testid="object-detection-tool-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <div className="mt-2">
        <p className="text-sm font-medium">Detected objects ({result.detections.length})</p>
        {result.detections.length > 0 ? (
          <ul className="mt-1 space-y-1 text-sm" data-testid="object-detection-list">
            {result.detections.map((detection, index) => (
              <li className="rounded border px-2 py-1" key={`${detection.label}-${index}`}>
                {detection.label} [{detection.bbox_xyxy_px.join(", ")}]
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-600">No confident objects detected.</p>
        )}
      </div>
    </section>
  );
}
