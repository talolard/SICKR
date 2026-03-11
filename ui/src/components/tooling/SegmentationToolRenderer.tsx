import { useState } from "react";
import type { ReactElement } from "react";

import { ImageToolOutputRenderer } from "./ImageToolOutputRenderer";
import type { AttachmentRef } from "../../lib/attachments";
import type { AnalysisFeedbackKind } from "@/lib/api/threadDataClient";

export type SegmentationMask = {
  label: string;
  query?: string | null;
  score?: number | null;
  bbox_xyxy_px?: [number, number, number, number] | null;
  mask_image: AttachmentRef;
};

export type SegmentationQueryResult = {
  query: string;
  status: "matched" | "unattributed" | "no_match";
  matched_mask_count: number;
};

export type SegmentationFeedbackInput = {
  feedbackKind: AnalysisFeedbackKind;
  maskOrdinal: number;
  maskLabel: string;
  queryText?: string;
};

export type SegmentationToolResult = {
  caption: string;
  images: AttachmentRef[];
  prompt: string;
  queries: string[];
  query_results: SegmentationQueryResult[];
  analysis_id?: string | null;
  masks: SegmentationMask[];
};

type SegmentationToolRendererProps = {
  result: SegmentationToolResult;
  onSubmitFeedback?: (payload: SegmentationFeedbackInput) => Promise<void>;
};

export function SegmentationToolRenderer(props: SegmentationToolRendererProps): ReactElement {
  const { result } = props;
  const [savingMaskOrdinal, setSavingMaskOrdinal] = useState<number | null>(null);
  const [savedFeedback, setSavedFeedback] = useState<Record<number, AnalysisFeedbackKind>>({});
  const [feedbackError, setFeedbackError] = useState<string | null>(null);

  async function submitFeedback(payload: SegmentationFeedbackInput): Promise<void> {
    if (!props.onSubmitFeedback) {
      return;
    }
    setFeedbackError(null);
    setSavingMaskOrdinal(payload.maskOrdinal);
    try {
      await props.onSubmitFeedback(payload);
      setSavedFeedback((previous) => ({
        ...previous,
        [payload.maskOrdinal]: payload.feedbackKind,
      }));
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to save segmentation feedback.";
      setFeedbackError(message);
    } finally {
      setSavingMaskOrdinal(null);
    }
  }

  return (
    <section className="rounded border bg-white p-2" data-testid="segmentation-tool-output">
      <ImageToolOutputRenderer caption={result.caption} images={result.images} />
      <p className="mt-2 text-sm font-medium">Prompt: {result.prompt}</p>
      {result.queries.length > 0 ? (
        <p className="mt-1 text-xs text-gray-600">Queries: {result.queries.join(", ")}</p>
      ) : null}
      {result.query_results.length > 0 ? (
        <ul
          className="mt-2 space-y-1 text-xs text-gray-700"
          data-testid="segmentation-query-summary"
        >
          {result.query_results.map((summary) => (
            <li className="rounded border px-2 py-1" key={summary.query}>
              <span className="font-medium">{summary.query}</span>: {summary.status} (
              {summary.matched_mask_count})
            </li>
          ))}
        </ul>
      ) : null}
      <div className="mt-1 text-sm text-gray-700">
        {result.masks.length > 0 ? (
          <ul className="space-y-1" data-testid="segmentation-mask-list">
            {result.masks.map((mask, index) => (
              <li className="rounded border px-2 py-1" key={`${mask.label}-${index}`}>
                <p className="font-medium">{mask.label}</p>
                {mask.query ? <p className="text-xs text-gray-600">Query: {mask.query}</p> : null}
                {typeof mask.score === "number" ? (
                  <p className="text-xs text-gray-600">Score: {mask.score.toFixed(3)}</p>
                ) : null}
                {mask.bbox_xyxy_px ? (
                  <p className="text-xs text-gray-600">
                    BBox: [{mask.bbox_xyxy_px.join(", ")}]
                  </p>
                ) : null}
                {props.onSubmitFeedback ? (
                  <div className="mt-2 flex items-center gap-2">
                    <button
                      className="rounded border border-green-400 px-2 py-1 text-xs text-green-700 disabled:opacity-60"
                      disabled={savingMaskOrdinal === index + 1}
                      onClick={() =>
                        void submitFeedback({
                          feedbackKind: "confirm",
                          maskOrdinal: index + 1,
                          maskLabel: mask.label,
                          ...(mask.query ? { queryText: mask.query } : {}),
                        })
                      }
                      type="button"
                    >
                      Confirm
                    </button>
                    <button
                      className="rounded border border-red-400 px-2 py-1 text-xs text-red-700 disabled:opacity-60"
                      disabled={savingMaskOrdinal === index + 1}
                      onClick={() =>
                        void submitFeedback({
                          feedbackKind: "reject",
                          maskOrdinal: index + 1,
                          maskLabel: mask.label,
                          ...(mask.query ? { queryText: mask.query } : {}),
                        })
                      }
                      type="button"
                    >
                      Reject
                    </button>
                    {savedFeedback[index + 1] ? (
                      <span className="text-xs text-gray-500">
                        Saved: {savedFeedback[index + 1]}
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p>No masks returned.</p>
        )}
      </div>
      {feedbackError ? <p className="mt-2 text-xs text-red-700">{feedbackError}</p> : null}
    </section>
  );
}
