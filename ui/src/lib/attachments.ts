export type AttachmentRef = {
  attachment_id: string;
  mime_type: string;
  uri: string;
  width: number | null;
  height: number | null;
  file_name?: string | null;
};

export type UploadStatus = "uploading" | "ready" | "error";

export type PendingAttachment = {
  localId: string;
  fileName: string;
  mimeType: string;
  progress: number;
  status: UploadStatus;
  attachmentRef?: AttachmentRef;
  errorMessage?: string;
};
