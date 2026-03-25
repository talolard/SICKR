"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactElement } from "react";

import { AttachmentComposer } from "@/components/attachments/AttachmentComposer";
import type { AttachmentRef, PendingAttachment } from "@/lib/attachments";

type AgentImageAttachmentPanelProps = {
  threadId: string | null;
  onReadyAttachmentsChange: (attachments: AttachmentRef[]) => void;
  helperText?: string;
};

function attachmentErrorMessage(status: number, body: string): string {
  if (body.length > 0) {
    return `Upload failed with status ${status}: ${body}`;
  }
  return `Upload failed with status ${status}.`;
}

export function AgentImageAttachmentPanel({
  threadId,
  onReadyAttachmentsChange,
  helperText = "Uploaded images are added to image-analysis tool context for this thread.",
}: AgentImageAttachmentPanelProps): ReactElement {
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const attachmentFilesRef = useRef<Record<string, File>>({});

  useEffect(() => {
    attachmentFilesRef.current = {};
    setAttachments([]);
  }, [threadId]);

  useEffect(() => {
    const readyAttachments = attachments
      .filter((attachment) => attachment.status === "ready" && attachment.attachmentRef)
      .map((attachment) => attachment.attachmentRef as AttachmentRef);
    onReadyAttachmentsChange(readyAttachments);
  }, [attachments, onReadyAttachmentsChange]);

  const uploadAttachment = async (localId: string, file: File): Promise<void> => {
    if (!threadId) {
      const message = "Create or select a thread before uploading images.";
      setAttachments((current) =>
        current.map((attachment) =>
          attachment.localId === localId
            ? { ...attachment, status: "error", errorMessage: message }
            : attachment,
        ),
      );
      return;
    }
    try {
      const response = await fetch("/api/attachments", {
        method: "POST",
        headers: {
          "content-type": file.type || "application/octet-stream",
          "x-filename": file.name,
          "x-thread-id": threadId,
        },
        body: file,
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(attachmentErrorMessage(response.status, body));
      }
      const attachmentRef = (await response.json()) as AttachmentRef;
      setAttachments((current) =>
        current.map((attachment) =>
          attachment.localId === localId
            ? { ...attachment, status: "ready", progress: 100, attachmentRef }
            : attachment,
        ),
      );
    } catch (uploadError: unknown) {
      const message =
        uploadError instanceof Error ? uploadError.message : "Upload failed unexpectedly.";
      setAttachments((current) =>
        current.map((attachment) =>
          attachment.localId === localId
            ? { ...attachment, status: "error", errorMessage: message }
            : attachment,
        ),
      );
    }
  };

  const handleFilesSelected = (fileList: FileList): void => {
    const files = Array.from(fileList);
    const nextAttachments: PendingAttachment[] = files.map((file) => {
      const localId = crypto.randomUUID();
      attachmentFilesRef.current[localId] = file;
      return {
        localId,
        fileName: file.name,
        mimeType: file.type,
        progress: 0,
        status: "uploading",
      };
    });
    setAttachments((current) => [...current, ...nextAttachments]);
    nextAttachments.forEach((attachment, index) => {
      const file = files[index];
      if (file) {
        void uploadAttachment(attachment.localId, file);
      }
    });
  };

  const handleRemoveAttachment = (localId: string): void => {
    delete attachmentFilesRef.current[localId];
    setAttachments((current) =>
      current.filter((attachment) => attachment.localId !== localId),
    );
  };

  const handleRetryAttachment = (localId: string): void => {
    const file = attachmentFilesRef.current[localId];
    if (!file) {
      return;
    }
    setAttachments((current) =>
      current.map((attachment) =>
        attachment.localId === localId
          ? (() => {
              const nextAttachment: PendingAttachment = {
                ...attachment,
                status: "uploading",
                progress: 0,
              };
              delete nextAttachment.errorMessage;
              return nextAttachment;
            })()
          : attachment,
      ),
    );
    void uploadAttachment(localId, file);
  };

  return (
    <section data-testid="agent-image-attachment-panel">
      <AttachmentComposer
        attachments={attachments}
        inputId="agent-image-attachment-input"
        label="Upload room images"
        onFilesSelected={handleFilesSelected}
        onRemoveAttachment={handleRemoveAttachment}
        onRetryAttachment={handleRetryAttachment}
      />
      <p className="mt-3 px-1 text-xs leading-5 text-on-surface-variant">
        {helperText}
      </p>
    </section>
  );
}
