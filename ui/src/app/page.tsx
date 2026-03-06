"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactElement } from "react";
import { CopilotSidebar, useAgent } from "@copilotkit/react-core/v2";

import { AttachmentComposer } from "@/components/attachments/AttachmentComposer";
import { useThreadSession } from "@/app/CopilotKitProviders";
import { CopilotToolRenderers } from "@/components/copilotkit/CopilotToolRenderers";
import type { AttachmentRef, PendingAttachment } from "@/lib/attachments";

function resolveAttachmentUri(uri: string): string {
  if (uri.startsWith("http://") || uri.startsWith("https://") || uri.startsWith("data:")) {
    return uri;
  }
  if (uri.startsWith("/attachments/")) {
    return uri;
  }
  return `/attachments/${uri.replace(/^\/+/, "")}`;
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
  const attachmentFilesRef = useRef<Record<string, File>>({});

  const pendingUploads = attachments.some((attachment) => attachment.status === "uploading");

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
    });
  }, [agent, attachments, threadId]);

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

  const uploadAttachment = async (localId: string, file: File): Promise<void> => {
    await new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/attachments");
      xhr.setRequestHeader("content-type", file.type || "application/octet-stream");
      xhr.setRequestHeader("x-filename", file.name);
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
        resolve();
      };
      xhr.send(file);
    }).catch((uploadError) => {
      const message =
        uploadError instanceof Error ? uploadError.message : "Upload failed unexpectedly.";
      setAttachmentError(localId, message);
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
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 p-6">
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
        <p className="text-xs text-gray-500">
          Debug harness: <a className="underline" href="/debug/agui-harness">/debug/agui-harness</a>
        </p>
      </header>
      <AttachmentComposer
        attachments={attachments}
        onFilesSelected={handleFilesSelected}
        onRemoveAttachment={handleRemoveAttachment}
        onRetryAttachment={handleRetryAttachment}
      />
      {pendingUploads ? (
        <p className="text-sm text-amber-700">Finish uploading images before sending.</p>
      ) : null}
      <CopilotToolRenderers />
      <CopilotSidebar />
    </main>
  );
}
