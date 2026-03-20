"use client";

import type { ChangeEvent, ReactElement } from "react";

import type { PendingAttachment } from "@/lib/attachments";

type AttachmentComposerProps = {
  attachments: PendingAttachment[];
  onFilesSelected: (files: FileList) => void;
  onRemoveAttachment: (localId: string) => void;
  onRetryAttachment: (localId: string) => void;
  accept?: string;
  inputId?: string;
  label?: string;
};

export function AttachmentComposer({
  attachments,
  onFilesSelected,
  onRemoveAttachment,
  onRetryAttachment,
  accept = "image/png,image/jpeg,image/webp",
  inputId = "attachment-input",
  label = "Attach images",
}: AttachmentComposerProps): ReactElement {
  const handleFileSelection = (event: ChangeEvent<HTMLInputElement>): void => {
    if (event.target.files) {
      onFilesSelected(event.target.files);
    }
    event.target.value = "";
  };

  return (
    <section className="editorial-panel-elevated flex flex-col gap-4 rounded-[30px] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="editorial-eyebrow">Image intake</p>
          <label className="mt-2 block text-base font-semibold text-primary" htmlFor={inputId}>
            {label}
          </label>
          <p className="mt-2 text-sm leading-6 text-on-surface-variant">
            Add PNG, JPEG, or WEBP room images without dropping back to the browser-default file
            input.
          </p>
        </div>
        <label
          className="cursor-pointer rounded-full bg-[color:var(--primary)] px-4 py-2 text-sm font-semibold text-white shadow-[0_16px_30px_rgba(24,36,27,0.16)]"
          htmlFor={inputId}
        >
          Choose images
        </label>
      </div>
      <input
        accept={accept}
        className="sr-only"
        data-testid="attachment-input"
        id={inputId}
        multiple
        onChange={handleFileSelection}
        type="file"
      />
      <div className="flex flex-col gap-3" data-testid="attachment-list">
        {attachments.length === 0 ? (
          <div className="rounded-[24px] bg-[color:var(--surface-container-low)] px-4 py-4 text-sm leading-6 text-on-surface-variant">
            Uploaded images will appear here once they are attached to the current thread.
          </div>
        ) : null}
        {attachments.map((attachment) => (
          <div
            className="rounded-[24px] bg-[color:var(--surface-container-low)] px-4 py-4 shadow-[var(--panel-shadow)]"
            data-testid={`attachment-${attachment.localId}`}
            key={attachment.localId}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-primary">{attachment.fileName}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-on-surface-variant">
                  {attachment.status} ({attachment.progress}%)
                </p>
              </div>
              <div className="rounded-full bg-[color:var(--surface-container-lowest)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                {attachment.status}
              </div>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-[rgba(24,36,27,0.08)]">
              <div
                className="h-full rounded-full bg-[color:var(--primary)]"
                style={{ width: `${attachment.progress}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-on-surface-variant">
              {attachment.mimeType || "Unknown file type"}
            </p>
            {attachment.errorMessage ? (
              <p className="mt-2 text-xs text-red-600">{attachment.errorMessage}</p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                className="rounded-full bg-[color:var(--surface-container-lowest)] px-3 py-1.5 text-xs font-semibold text-primary"
                onClick={() => onRemoveAttachment(attachment.localId)}
                type="button"
              >
                Remove
              </button>
              {attachment.status === "error" ? (
                <button
                  className="rounded-full bg-[color:var(--secondary-container)] px-3 py-1.5 text-xs font-semibold text-[#5b3612]"
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
