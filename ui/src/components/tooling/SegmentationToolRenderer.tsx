import type { ReactElement } from "react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";
import type { AttachmentRef } from "../../lib/attachments";

export type SegmentationMask = {
  label: string;
  mask_image: AttachmentRef;
};

export type SegmentationToolResult = {
  caption: string;
  images: AttachmentRef[];
  prompt: string;
  masks: SegmentationMask[];
};

type SegmentationToolRendererProps = {
  result: SegmentationToolResult;
};

export function SegmentationToolRenderer(props: SegmentationToolRendererProps): ReactElement {
  const { result } = props;
  return (
    <section className="rounded border bg-white p-2" data-testid="segmentation-tool-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <p className="mt-2 text-sm font-medium">Prompt: {result.prompt}</p>
      <div className="mt-1 text-sm text-gray-700">
        {result.masks.length > 0 ? (
          <ul className="space-y-1" data-testid="segmentation-mask-list">
            {result.masks.map((mask, index) => (
              <li className="rounded border px-2 py-1" key={`${mask.label}-${index}`}>
                {mask.label}
              </li>
            ))}
          </ul>
        ) : (
          <p>No masks returned.</p>
        )}
      </div>
    </section>
  );
}
