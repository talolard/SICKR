import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { AgentImageAttachmentPanel } from "./AgentImageAttachmentPanel";

describe("AgentImageAttachmentPanel", () => {
  it("uploads files and emits ready attachments", async () => {
    const onReadyAttachmentsChange = vi.fn();
    const fetchSpy = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            attachment_id: "att-1",
            mime_type: "image/png",
            uri: "/attachments/att-1",
            width: 1200,
            height: 800,
            file_name: "room.png",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      );

    render(
      <AgentImageAttachmentPanel
        onReadyAttachmentsChange={onReadyAttachmentsChange}
        threadId="agent-image-analysis-thread"
      />,
    );

    const input = screen.getByTestId("attachment-input");
    const file = new File(["image-bytes"], "room.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(onReadyAttachmentsChange).toHaveBeenLastCalledWith([
        {
          attachment_id: "att-1",
          mime_type: "image/png",
          uri: "/attachments/att-1",
          width: 1200,
          height: 800,
          file_name: "room.png",
        },
      ]);
    });
  });
});
