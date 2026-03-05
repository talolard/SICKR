"use client";

import type { ChangeEvent, ReactElement } from "react";

import type { PendingAttachment } from "@/lib/attachments";

type AttachmentComposerProps = {
  attachments: PendingAttachment[];
  onFilesSelected: (files: FileList) => void;
  onRemoveAttachment: (localId: string) => void;
  onRetryAttachment: (localId: string) => void;
};

export function AttachmentComposer({
  attachments,
  onFilesSelected,
  onRemoveAttachment,
  onRetryAttachment,
}: AttachmentComposerProps): ReactElement {
  const handleFileSelection = (event: ChangeEvent<HTMLInputElement>): void => {
    if (event.target.files) {
      onFilesSelected(event.target.files);
    }
    event.target.value = "";
  };

  return (
    <section className="flex flex-col gap-2 rounded border p-3">
      <label className="text-sm font-medium" htmlFor="attachment-input">
        Attach images
      </label>
      <input
        accept="image/png,image/jpeg,image/webp"
        data-testid="attachment-input"
        id="attachment-input"
        multiple
        onChange={handleFileSelection}
        type="file"
      />
      <div className="flex flex-col gap-2" data-testid="attachment-list">
        {attachments.map((attachment) => (
          <div
            className="rounded border p-2"
            data-testid={`attachment-${attachment.localId}`}
            key={attachment.localId}
          >
            <p className="text-sm font-medium">{attachment.fileName}</p>
            <p className="text-xs text-gray-700">
              {attachment.status} ({attachment.progress}%)
            </p>
            {attachment.errorMessage ? (
              <p className="text-xs text-red-600">{attachment.errorMessage}</p>
            ) : null}
            <div className="mt-1 flex gap-2">
              <button
                className="rounded border px-2 py-1 text-xs"
                onClick={() => onRemoveAttachment(attachment.localId)}
                type="button"
              >
                Remove
              </button>
              {attachment.status === "error" ? (
                <button
                  className="rounded border px-2 py-1 text-xs"
                  onClick={() => onRetryAttachment(attachment.localId)}
                  type="button"
                >
                  Retry upload
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
