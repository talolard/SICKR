import type { ReactElement } from "react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";
import type { AttachmentRef } from "../../lib/attachments";

export type DepthParametersUsed = {
  ensemble_size: number;
  processing_res: number;
  resample_method: "bilinear" | "nearest" | "bicubic";
  seed: number;
  output_format: "png" | "jpg" | "webp";
};

export type DepthEstimationToolResult = {
  caption: string;
  images: AttachmentRef[];
  parameters_used: DepthParametersUsed;
};

type DepthEstimationToolRendererProps = {
  result: DepthEstimationToolResult;
};

export function DepthEstimationToolRenderer(
  props: DepthEstimationToolRendererProps,
): ReactElement {
  const { result } = props;
  return (
    <section className="space-y-3" data-testid="depth-estimation-tool-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <div className="rounded-[22px] bg-[color:var(--surface-container-low)] px-4 py-4">
        <p className="editorial-eyebrow">Depth settings</p>
        <p className="mt-3 text-xs leading-6 text-on-surface-variant">
          Params: ensemble {result.parameters_used.ensemble_size}, resolution{" "}
          {result.parameters_used.processing_res}, resample{" "}
          {result.parameters_used.resample_method}, seed {result.parameters_used.seed}, format{" "}
          {result.parameters_used.output_format}
        </p>
      </div>
    </section>
  );
}
