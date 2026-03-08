"use client";

import { useEffect, useRef, useState } from "react";
import type { ClipboardEvent, ReactElement } from "react";
import { CopilotSidebar, useAgent } from "@copilotkit/react-core/v2";

import { AttachmentComposer } from "@/components/attachments/AttachmentComposer";
import { useThreadSession } from "@/app/CopilotKitProviders";
import { CopilotToolRenderers } from "@/components/copilotkit/CopilotToolRenderers";
import { ThreadDataPanel } from "@/components/thread/ThreadDataPanel";
import type { AttachmentRef, PendingAttachment } from "@/lib/attachments";
import { FloorPlanPreviewPanel } from "@/components/tooling/FloorPlanPreviewPanel";
import { subscribeFloorPlanRendered } from "@/lib/floorPlanPreviewEvents";
import {
  type FloorPlanPreviewState,
  loadFloorPlanPreview,
  saveFloorPlanPreview,
} from "@/lib/floorPlanPreviewStore";
import { createRoom3DSnapshot } from "@/lib/api/room3dClient";
import {
  type Room3DSnapshotContext,
  loadRoom3DSnapshots,
  saveRoom3DSnapshots,
} from "@/lib/threadStore";
import { getConsoleRecordsSnapshot, startFeedbackCapture } from "@/lib/feedbackCapture";

const DEFAULT_FEEDBACK_TITLE = "user_comment_from_ui";

type FeedbackCreateResponse = {
  comment_id: string;
  directory: string;
  markdown_path: string;
  saved_images_count: number;
};

function resolveAttachmentUri(uri: string): string {
  if (uri.startsWith("http://") || uri.startsWith("https://") || uri.startsWith("data:")) {
    return uri;
  }
  if (uri.startsWith("/attachments/")) {
    return uri;
  }
  return `/attachments/${uri.replace(/^\/+/, "")}`;
}

function collectStorageByPrefix(storage: Storage, prefix: string): Record<string, unknown> {
  const collected: Record<string, unknown> = {};
  for (let index = 0; index < storage.length; index += 1) {
    const key = storage.key(index);
    if (!key || !key.startsWith(prefix)) {
      continue;
    }
    const raw = storage.getItem(key);
    if (!raw) {
      continue;
    }
    try {
      collected[key] = JSON.parse(raw) as unknown;
    } catch {
      collected[key] = raw;
    }
  }
  return collected;
}

export default function Home(): ReactElement {
  const { agent } = useAgent({ agentId: "ikea_agent" });
  const {
    threadId,
    threadIds,
    warning: threadWarning,
    selectThread,
    createThread,
    clearWarning,
  } = useThreadSession();
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [floorPlanPreview, setFloorPlanPreview] = useState<FloorPlanPreviewState | null>(null);
  const [room3dSnapshots, setRoom3dSnapshots] = useState<Room3DSnapshotContext[]>([]);
  const attachmentFilesRef = useRef<Record<string, File>>({});
  const [isFeedbackOpen, setIsFeedbackOpen] = useState<boolean>(false);
  const [feedbackTitle, setFeedbackTitle] = useState<string>(DEFAULT_FEEDBACK_TITLE);
  const [feedbackComment, setFeedbackComment] = useState<string>("");
  const [feedbackAttachments, setFeedbackAttachments] = useState<PendingAttachment[]>([]);
  const feedbackFilesRef = useRef<Record<string, File>>({});
  const [includeConsoleLog, setIncludeConsoleLog] = useState<boolean>(true);
  const [includeDomSnapshot, setIncludeDomSnapshot] = useState<boolean>(true);
  const [includeUiState, setIncludeUiState] = useState<boolean>(true);
  const [isSendingFeedback, setIsSendingFeedback] = useState<boolean>(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackSuccessPath, setFeedbackSuccessPath] = useState<string | null>(null);

  const pendingUploads = attachments.some((attachment) => attachment.status === "uploading");
  const pendingFeedbackUploads = feedbackAttachments.some(
    (attachment) => attachment.status === "uploading",
  );

  useEffect(() => {
    startFeedbackCapture();
  }, []);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    const readyAttachments = attachments
      .filter((attachment) => attachment.status === "ready" && attachment.attachmentRef)
      .map((attachment) => attachment.attachmentRef as AttachmentRef)
      .map((attachment) => ({
        ...attachment,
        uri: resolveAttachmentUri(attachment.uri),
      }));
    // TODO: support explicit "continue thread" vs "branch thread" semantics.
    const previousState =
      typeof agent.state === "object" && agent.state !== null
        ? (agent.state as Record<string, unknown>)
        : {};
    agent.setState({
      ...previousState,
      session_id: threadId,
      attachments: readyAttachments,
      room_3d_snapshots: room3dSnapshots,
    });
  }, [agent, attachments, room3dSnapshots, threadId]);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    setFloorPlanPreview(loadFloorPlanPreview(threadId));
    setRoom3dSnapshots(loadRoom3DSnapshots(threadId));
  }, [threadId]);

  useEffect(() => {
    const unsubscribe = subscribeFloorPlanRendered((detail) => {
      const resolvedImages = detail.images.map((image) => ({
        ...image,
        uri: resolveAttachmentUri(image.uri),
      }));
      const nextSnapshot: FloorPlanPreviewState = {
        ...detail,
        images: resolvedImages,
        threadId: threadId ?? "pending",
      };
      setFloorPlanPreview(nextSnapshot);
      if (threadId) {
        saveFloorPlanPreview(nextSnapshot);
      }
    });
    return unsubscribe;
  }, [threadId]);

  const setAttachmentProgress = (localId: string, progress: number): void => {
    setAttachments((current) =>
      current.map((attachment) =>
        attachment.localId === localId ? { ...attachment, progress } : attachment,
      ),
    );
  };

  const setAttachmentReady = (localId: string, attachmentRef: AttachmentRef): void => {
    setAttachments((current) =>
      current.map((attachment) =>
        attachment.localId === localId
          ? {
              ...attachment,
              status: "ready",
              progress: 100,
              attachmentRef: {
                ...attachmentRef,
                uri: resolveAttachmentUri(attachmentRef.uri),
              },
            }
          : attachment,
      ),
    );
  };

  const setAttachmentError = (localId: string, message: string): void => {
    setAttachments((current) =>
      current.map((attachment) =>
        attachment.localId === localId
          ? { ...attachment, status: "error", errorMessage: message }
          : attachment,
      ),
    );
  };

  const uploadAttachment = async (localId: string, file: File): Promise<AttachmentRef | null> => {
    return new Promise<AttachmentRef>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/attachments");
      xhr.setRequestHeader("content-type", file.type || "application/octet-stream");
      xhr.setRequestHeader("x-filename", file.name);
      if (threadId) {
        xhr.setRequestHeader("x-thread-id", threadId);
      }
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) {
          return;
        }
        const percent = Math.round((event.loaded / event.total) * 100);
        setAttachmentProgress(localId, percent);
      };
      xhr.onerror = () => reject(new Error("Upload failed due to network error."));
      xhr.onload = () => {
        if (xhr.status < 200 || xhr.status >= 300) {
          reject(new Error(`Upload failed with status ${xhr.status}`));
          return;
        }
        const payload = JSON.parse(xhr.responseText) as AttachmentRef;
        setAttachmentReady(localId, payload);
        resolve(payload);
      };
      xhr.send(file);
    }).catch((uploadError) => {
      const message =
        uploadError instanceof Error ? uploadError.message : "Upload failed unexpectedly.";
      setAttachmentError(localId, message);
      return null;
    });
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
    nextAttachments.forEach((pendingAttachment) => {
      const file = attachmentFilesRef.current[pendingAttachment.localId];
      if (!file) {
        setAttachmentError(pendingAttachment.localId, "Missing local file handle.");
        return;
      }
      void uploadAttachment(pendingAttachment.localId, file);
    });
  };

  const dataUrlToFile = (dataUrl: string, fileName: string): File => {
    const [prefix, payload] = dataUrl.split(",", 2);
    if (!prefix || !payload) {
      throw new Error("Snapshot payload is malformed.");
    }
    const mimeMatch = prefix.match(/^data:(.*?);base64$/);
    const mimeType = mimeMatch?.[1] ?? "image/png";
    const binary = atob(payload);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new File([bytes], fileName, { type: mimeType });
  };

  const handleRoom3DSnapshotCaptured = async (
    snapshot: Omit<Room3DSnapshotContext, "snapshot_id" | "attachment"> & {
      image_data_url: string;
    },
  ): Promise<void> => {
    const localId = crypto.randomUUID();
    const fileName = `room-3d-snapshot-${localId.slice(0, 8)}.png`;
    const file = dataUrlToFile(snapshot.image_data_url, fileName);
    attachmentFilesRef.current[localId] = file;
    setAttachments((current) => [
      ...current,
      {
        localId,
        fileName,
        mimeType: "image/png",
        progress: 0,
        status: "uploading",
      },
    ]);
    const uploaded = await uploadAttachment(localId, file);
    if (!uploaded || !threadId) {
      return;
    }
    let persistedSnapshotId = `snapshot-${localId}`;
    try {
      const persisted = await createRoom3DSnapshot(threadId, {
        snapshot_asset_id: uploaded.attachment_id,
        room_3d_asset_id: null,
        camera: snapshot.camera,
        lighting: snapshot.lighting,
        comment: snapshot.comment,
        run_id: null,
      });
      persistedSnapshotId = persisted.room_3d_snapshot_id;
    } catch {
      // Keep local snapshot context even when persistence API is temporarily unavailable.
    }
    setRoom3dSnapshots((current) => {
      const next: Room3DSnapshotContext[] = [
        ...current,
        {
          snapshot_id: persistedSnapshotId,
          attachment: {
            ...uploaded,
            uri: resolveAttachmentUri(uploaded.uri),
          },
          comment: snapshot.comment,
          captured_at: snapshot.captured_at,
          camera: snapshot.camera,
          lighting: snapshot.lighting,
        },
      ];
      saveRoom3DSnapshots(threadId, next);
      return next;
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

  const addFeedbackFiles = (files: File[]): void => {
    const next = files.map((file) => {
      const localId = crypto.randomUUID();
      feedbackFilesRef.current[localId] = file;
      return {
        localId,
        fileName: file.name,
        mimeType: file.type,
        progress: 0,
        status: "uploading" as const,
      };
    });
    setFeedbackAttachments((current) => [...current, ...next]);
    next.forEach((pendingAttachment) => {
      const file = feedbackFilesRef.current[pendingAttachment.localId];
      if (!file) {
        return;
      }
      const upload = new XMLHttpRequest();
      upload.open("POST", "/api/attachments");
      upload.setRequestHeader("content-type", file.type || "application/octet-stream");
      upload.setRequestHeader("x-filename", file.name);
      if (threadId) {
        upload.setRequestHeader("x-thread-id", threadId);
      }
      upload.upload.onprogress = (event) => {
        if (!event.lengthComputable) {
          return;
        }
        const percent = Math.round((event.loaded / event.total) * 100);
        setFeedbackAttachments((current) =>
          current.map((attachment) =>
            attachment.localId === pendingAttachment.localId
              ? { ...attachment, progress: percent }
              : attachment,
          ),
        );
      };
      upload.onerror = () => {
        setFeedbackAttachments((current) =>
          current.map((attachment) =>
            attachment.localId === pendingAttachment.localId
              ? { ...attachment, status: "error", errorMessage: "Upload failed due to network error." }
              : attachment,
          ),
        );
      };
      upload.onload = () => {
        if (upload.status < 200 || upload.status >= 300) {
          setFeedbackAttachments((current) =>
            current.map((attachment) =>
              attachment.localId === pendingAttachment.localId
                ? {
                    ...attachment,
                    status: "error",
                    errorMessage: `Upload failed with status ${upload.status}`,
                  }
                : attachment,
            ),
          );
          return;
        }
        const payload = JSON.parse(upload.responseText) as AttachmentRef;
        setFeedbackAttachments((current) =>
          current.map((attachment) =>
            attachment.localId === pendingAttachment.localId
              ? {
                  ...attachment,
                  status: "ready",
                  progress: 100,
                  attachmentRef: {
                    ...payload,
                    uri: resolveAttachmentUri(payload.uri),
                  },
                }
              : attachment,
          ),
        );
      };
      upload.send(file);
    });
  };

  const handleFeedbackFileSelection = (fileList: FileList): void => {
    addFeedbackFiles(Array.from(fileList));
  };

  const handleFeedbackPaste = (event: ClipboardEvent<HTMLDivElement>): void => {
    const pastedFiles = Array.from(event.clipboardData.items)
      .filter((item) => item.kind === "file")
      .map((item) => item.getAsFile())
      .filter((file): file is File => file !== null);
    if (pastedFiles.length === 0) {
      return;
    }
    event.preventDefault();
    addFeedbackFiles(pastedFiles);
  };

  const handleRemoveFeedbackAttachment = (localId: string): void => {
    delete feedbackFilesRef.current[localId];
    setFeedbackAttachments((current) =>
      current.filter((attachment) => attachment.localId !== localId),
    );
  };

  const handleRetryFeedbackAttachment = (localId: string): void => {
    const file = feedbackFilesRef.current[localId];
    if (!file) {
      return;
    }
    setFeedbackAttachments((current) =>
      current.map((attachment) =>
        attachment.localId === localId
          ? (() => {
              const nextAttachment: PendingAttachment = {
                ...attachment,
                status: "uploading",
                progress: 0,
              };
              delete nextAttachment.errorMessage;
              delete nextAttachment.attachmentRef;
              return nextAttachment;
            })()
          : attachment,
      ),
    );
    addFeedbackFiles([file]);
    handleRemoveFeedbackAttachment(localId);
  };

  const buildUiStateSnapshot = (): Record<string, unknown> => {
    const viewport =
      typeof window === "undefined"
        ? null
        : { width: window.innerWidth, height: window.innerHeight, dpr: window.devicePixelRatio };
    return {
      thread_id: threadId,
      location: typeof window === "undefined" ? null : window.location.href,
      viewport,
      floor_plan_preview: floorPlanPreview,
      room_3d_snapshots: room3dSnapshots,
      chat_attachment_count: attachments.length,
      feedback_attachment_count: feedbackAttachments.length,
      local_storage: typeof window === "undefined" ? {} : collectStorageByPrefix(window.localStorage, "copilotkit_ui_"),
      session_storage:
        typeof window === "undefined" ? {} : collectStorageByPrefix(window.sessionStorage, "copilotkit_ui_"),
    };
  };

  const submitFeedback = async (): Promise<void> => {
    if (isSendingFeedback) {
      return;
    }
    if (pendingFeedbackUploads) {
      setFeedbackError("Finish uploading feedback images before sending.");
      return;
    }
    const readyAttachmentIds = feedbackAttachments
      .filter((attachment) => attachment.status === "ready" && attachment.attachmentRef)
      .map((attachment) => (attachment.attachmentRef as AttachmentRef).attachment_id);
    const normalizedTitle = feedbackTitle.trim() || DEFAULT_FEEDBACK_TITLE;
    if (normalizedTitle === DEFAULT_FEEDBACK_TITLE && !feedbackComment.trim() && readyAttachmentIds.length === 0) {
      setFeedbackError("Add a comment, an image, or a custom title before sending.");
      return;
    }
    setIsSendingFeedback(true);
    setFeedbackError(null);
    setFeedbackSuccessPath(null);
    try {
      const payload: Record<string, unknown> = {
        title: normalizedTitle,
        comment: feedbackComment,
        thread_id: threadId ?? "",
        page_url: typeof window === "undefined" ? "" : window.location.href,
        user_agent: typeof window === "undefined" ? "" : window.navigator.userAgent,
        include_console_log: includeConsoleLog,
        include_dom_snapshot: includeDomSnapshot,
        include_ui_state: includeUiState,
        attachment_ids: readyAttachmentIds,
      };
      if (includeConsoleLog) {
        payload.console_log = JSON.stringify(getConsoleRecordsSnapshot());
      }
      if (includeDomSnapshot && typeof window !== "undefined") {
        payload.dom_snapshot = window.document.documentElement.outerHTML;
      }
      if (includeUiState) {
        payload.ui_state = JSON.stringify(buildUiStateSnapshot());
      }

      const response = await fetch("/api/comments", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Feedback submission failed with status ${response.status}`);
      }
      const feedbackResponse = (await response.json()) as FeedbackCreateResponse;
      setFeedbackSuccessPath(feedbackResponse.directory);
      setFeedbackComment("");
      setFeedbackAttachments([]);
      feedbackFilesRef.current = {};
      setFeedbackTitle(DEFAULT_FEEDBACK_TITLE);
    } catch (error) {
      setFeedbackError(
        error instanceof Error ? error.message : "Feedback submission failed unexpectedly.",
      );
    } finally {
      setIsSendingFeedback(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-[1700px] flex-col gap-4 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">IKEA Agent</h1>
        <p className="text-sm text-gray-600">
          Chat with the agent. Tool calls render inline.
        </p>
        <div className="mt-2 flex items-end gap-2">
          <label className="flex flex-col gap-1 text-xs text-gray-600">
            Thread
            <select
              className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900"
              disabled={!threadId}
              onChange={(event) => {
                selectThread(event.target.value);
              }}
              value={threadId ?? ""}
            >
              {(threadId && !threadIds.includes(threadId) ? [threadId, ...threadIds] : threadIds).map(
                (id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ),
              )}
            </select>
          </label>
          <button
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-800 hover:bg-gray-50"
            onClick={createThread}
            type="button"
          >
            New thread
          </button>
        </div>
        {threadWarning ? (
          <div className="mt-1 flex items-start gap-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
            <span>{threadWarning}</span>
            <button className="underline" onClick={clearWarning} type="button">
              Dismiss
            </button>
          </div>
        ) : null}
        {threadId ? <ThreadDataPanel threadId={threadId} /> : null}
        <p className="text-xs text-gray-500">
          Debug harness: <a className="underline" href="/debug/agui-harness">/debug/agui-harness</a>
        </p>
      </header>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
        <FloorPlanPreviewPanel
          onSnapshotCaptured={handleRoom3DSnapshotCaptured}
          preview={floorPlanPreview}
        />
        <section className="flex min-h-[60vh] flex-col gap-4">
          <AttachmentComposer
            attachments={attachments}
            onFilesSelected={handleFilesSelected}
            onRemoveAttachment={handleRemoveAttachment}
            onRetryAttachment={handleRetryAttachment}
          />
          {pendingUploads ? (
            <p className="text-sm text-amber-700">Finish uploading images before sending.</p>
          ) : null}
          <CopilotToolRenderers
            onFloorPlanRendered={(snapshot) => {
              const resolvedImages = snapshot.images.map((image) => ({
                ...image,
                uri: resolveAttachmentUri(image.uri),
              }));
              const nextSnapshot: FloorPlanPreviewState = {
                ...snapshot,
                threadId: threadId ?? "pending",
                images: resolvedImages,
              };
              setFloorPlanPreview(nextSnapshot);
              if (threadId) {
                saveFloorPlanPreview(nextSnapshot);
              }
            }}
          />
          <CopilotSidebar />
        </section>
      </div>
      <button
        className="fixed bottom-5 right-5 z-[2050] rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow hover:bg-gray-50"
        onClick={() => {
          setIsFeedbackOpen(true);
          setFeedbackError(null);
        }}
        type="button"
      >
        Feedback
      </button>
      {isFeedbackOpen ? (
        <div
          className="fixed inset-0 z-[2100] flex items-center justify-center bg-black/60 p-4"
          onClick={() => setIsFeedbackOpen(false)}
        >
          <section
            className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-4"
            onClick={(event) => event.stopPropagation()}
            onPaste={handleFeedbackPaste}
          >
            <header className="mb-3">
              <h2 className="text-lg font-semibold text-gray-900">Send feedback bundle</h2>
              <p className="text-sm text-gray-600">
                Add notes and screenshots. Optional debug data can be included for triage.
              </p>
            </header>
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-800" htmlFor="feedback-title">
                Title
              </label>
              <input
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
                id="feedback-title"
                onChange={(event) => setFeedbackTitle(event.target.value)}
                value={feedbackTitle}
              />
              <label className="block text-sm font-medium text-gray-800" htmlFor="feedback-comment">
                Comment
              </label>
              <textarea
                className="min-h-24 w-full rounded border border-gray-300 px-3 py-2 text-sm"
                id="feedback-comment"
                onChange={(event) => setFeedbackComment(event.target.value)}
                placeholder="Describe what you observed and what should be fixed."
                value={feedbackComment}
              />
              <div className="rounded border border-dashed border-gray-300 p-2 text-xs text-gray-600">
                Paste images directly while this dialog is focused, or use the file picker below.
              </div>
              <AttachmentComposer
                accept="image/png,image/jpeg,image/webp"
                attachments={feedbackAttachments}
                inputId="feedback-attachment-input"
                label="Feedback images"
                onFilesSelected={handleFeedbackFileSelection}
                onRemoveAttachment={handleRemoveFeedbackAttachment}
                onRetryAttachment={handleRetryFeedbackAttachment}
              />
              {pendingFeedbackUploads ? (
                <p className="text-xs text-amber-700">
                  Finish uploading feedback images before sending.
                </p>
              ) : null}
              <div className="space-y-1 rounded border p-2">
                <p className="text-xs font-medium text-gray-800">Include debug data</p>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={includeConsoleLog}
                    onChange={(event) => setIncludeConsoleLog(event.target.checked)}
                    type="checkbox"
                  />
                  Console log snapshot
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={includeDomSnapshot}
                    onChange={(event) => setIncludeDomSnapshot(event.target.checked)}
                    type="checkbox"
                  />
                  DOM snapshot
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={includeUiState}
                    onChange={(event) => setIncludeUiState(event.target.checked)}
                    type="checkbox"
                  />
                  UI state snapshot
                </label>
              </div>
              {feedbackError ? <p className="text-sm text-red-700">{feedbackError}</p> : null}
              {feedbackSuccessPath ? (
                <p className="text-sm text-green-700">Saved feedback bundle to {feedbackSuccessPath}</p>
              ) : null}
              <div className="flex justify-end gap-2">
                <button
                  className="rounded border border-gray-300 px-3 py-1.5 text-sm"
                  onClick={() => setIsFeedbackOpen(false)}
                  type="button"
                >
                  Close
                </button>
                <button
                  className="rounded border border-gray-300 bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-60"
                  disabled={isSendingFeedback || pendingFeedbackUploads}
                  onClick={() => {
                    void submitFeedback();
                  }}
                  type="button"
                >
                  {isSendingFeedback ? "Sending..." : "Send feedback"}
                </button>
              </div>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
