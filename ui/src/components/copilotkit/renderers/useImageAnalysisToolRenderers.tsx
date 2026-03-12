"use client";

import { useRenderTool } from "@copilotkit/react-core/v2";
import { z } from "zod";

import { createAnalysisFeedback } from "@/lib/api/threadDataClient";

import { parseDepthEstimationResult, parseObjectDetectionResult, parseRoomPhotoAnalysisResult, parseSegmentationResult } from "./parsing";
import { DefaultToolCard, LoadingToolMessage } from "./shared";
import { DepthEstimationToolRenderer } from "@/components/tooling/DepthEstimationToolRenderer";
import { ObjectDetectionToolRenderer } from "@/components/tooling/ObjectDetectionToolRenderer";
import { RoomPhotoAnalysisToolRenderer } from "@/components/tooling/RoomPhotoAnalysisToolRenderer";
import { SegmentationToolRenderer } from "@/components/tooling/SegmentationToolRenderer";
import { parseResult } from "@/lib/toolResultParsing";

type UseImageAnalysisToolRenderersOptions = {
  threadId?: string | null | undefined;
};

export function useImageAnalysisToolRenderers({
  threadId,
}: UseImageAnalysisToolRenderersOptions): void {
  useRenderTool({
    name: "detect_objects_in_image",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Detecting room objects..." />;
      }
      const parsed = parseObjectDetectionResult(result);
      if (parsed) {
        return <ObjectDetectionToolRenderer result={parsed} />;
      }
      return (
        <DefaultToolCard
          name="detect_objects_in_image"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage="Tool returned an invalid object-detection payload."
        />
      );
    },
  });

  useRenderTool({
    name: "estimate_depth_map",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Estimating depth map..." />;
      }
      const parsed = parseDepthEstimationResult(result);
      if (parsed) {
        return <DepthEstimationToolRenderer result={parsed} />;
      }
      return (
        <DefaultToolCard
          name="estimate_depth_map"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage="Tool returned an invalid depth payload."
        />
      );
    },
  });

  useRenderTool({
    name: "segment_image_with_prompt",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Segmenting image..." />;
      }
      const parsed = parseSegmentationResult(result);
      if (parsed) {
        const canPersistFeedback = Boolean(threadId) && Boolean(parsed.analysis_id);
        return (
          <SegmentationToolRenderer
            result={parsed}
            {...(canPersistFeedback
              ? {
                  onSubmitFeedback: async (payload) => {
                    await createAnalysisFeedback({
                      threadId: threadId as string,
                      analysisId: parsed.analysis_id as string,
                      payload: {
                        feedback_kind: payload.feedbackKind,
                        mask_ordinal: payload.maskOrdinal,
                        mask_label: payload.maskLabel,
                        ...(payload.queryText ? { query_text: payload.queryText } : {}),
                      },
                    });
                  },
                }
              : {})}
          />
        );
      }
      return (
        <DefaultToolCard
          name="segment_image_with_prompt"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage="Tool returned an invalid segmentation payload."
        />
      );
    },
  });

  useRenderTool({
    name: "analyze_room_photo",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <LoadingToolMessage message="Analyzing room photo..." />;
      }
      const parsed = parseRoomPhotoAnalysisResult(result);
      if (parsed) {
        return <RoomPhotoAnalysisToolRenderer result={parsed} />;
      }
      const parsedResult = parseResult(result);
      const errorMessage =
        typeof parsedResult === "string"
          ? parsedResult
          : "Tool returned an invalid room-analysis payload.";
      return (
        <DefaultToolCard
          name="analyze_room_photo"
          status="failed"
          result={undefined}
          args={undefined}
          errorMessage={errorMessage}
        />
      );
    },
  });
}
