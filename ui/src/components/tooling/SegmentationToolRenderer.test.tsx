import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { SegmentationToolRenderer } from "./SegmentationToolRenderer";

describe("SegmentationToolRenderer", () => {
  it("renders segmentation masks", () => {
    render(
      <SegmentationToolRenderer
        result={{
          caption: "Segmentation done",
          images: [],
          prompt: "clutter",
          queries: ["clutter", "bed"],
          query_results: [
            { query: "clutter", status: "unattributed", matched_mask_count: 1 },
            { query: "bed", status: "unattributed", matched_mask_count: 1 },
          ],
          masks: [
            {
              label: "mask-1",
              query: "clutter",
              score: 0.91,
              bbox_xyxy_px: [10, 20, 100, 120],
              mask_image: {
                attachment_id: "mask-1",
                mime_type: "image/png",
                uri: "/attachments/mask-1",
                width: 400,
                height: 300,
                file_name: "mask-1.png",
              },
            },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("segmentation-tool-output")).toBeInTheDocument();
    expect(screen.getByTestId("segmentation-mask-list")).toBeInTheDocument();
    expect(screen.getByTestId("segmentation-query-summary")).toBeInTheDocument();
    expect(screen.getByText("mask-1")).toBeInTheDocument();
  });

  it("renders empty mask state", () => {
    render(
      <SegmentationToolRenderer
        result={{
          caption: "Segmentation done",
          images: [],
          prompt: "clutter",
          queries: ["clutter"],
          query_results: [{ query: "clutter", status: "no_match", matched_mask_count: 0 }],
          masks: [],
        }}
      />,
    );

    expect(screen.getByText("No masks returned.")).toBeInTheDocument();
  });

  it("submits feedback for a mask", async () => {
    const onSubmitFeedback = vi.fn(async () => undefined);
    render(
      <SegmentationToolRenderer
        result={{
          caption: "Segmentation done",
          images: [],
          prompt: "clutter",
          queries: ["clutter"],
          query_results: [{ query: "clutter", status: "matched", matched_mask_count: 1 }],
          masks: [
            {
              label: "mask-1",
              query: "clutter",
              mask_image: {
                attachment_id: "mask-1",
                mime_type: "image/png",
                uri: "/attachments/mask-1",
                width: 400,
                height: 300,
                file_name: "mask-1.png",
              },
            },
          ],
        }}
        onSubmitFeedback={onSubmitFeedback}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => {
      expect(onSubmitFeedback).toHaveBeenCalledTimes(1);
    });
    expect(onSubmitFeedback).toHaveBeenCalledWith({
      feedbackKind: "confirm",
      maskOrdinal: 1,
      maskLabel: "mask-1",
      queryText: "clutter",
    });
    await screen.findByText("Saved: confirm");
  });
});
