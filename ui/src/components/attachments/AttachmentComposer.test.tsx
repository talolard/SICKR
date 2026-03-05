import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { AttachmentComposer } from "./AttachmentComposer";

describe("AttachmentComposer", () => {
  it("renders attachment status and actions", () => {
    const removeSpy = vi.fn();
    const retrySpy = vi.fn();
    render(
      <AttachmentComposer
        attachments={[
          {
            localId: "a1",
            fileName: "room.png",
            mimeType: "image/png",
            progress: 42,
            status: "error",
            errorMessage: "Upload failed",
          },
        ]}
        onFilesSelected={vi.fn()}
        onRemoveAttachment={removeSpy}
        onRetryAttachment={retrySpy}
      />,
    );

    expect(screen.getByText("room.png")).toBeInTheDocument();
    expect(screen.getByText("error (42%)")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Remove"));
    fireEvent.click(screen.getByText("Retry upload"));
    expect(removeSpy).toHaveBeenCalledWith("a1");
    expect(retrySpy).toHaveBeenCalledWith("a1");
  });
});
