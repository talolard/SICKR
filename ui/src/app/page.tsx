"use client";

import { FormEvent, useRef, useState } from "react";
import type { ReactElement } from "react";
import { AttachmentComposer } from "@/components/attachments/AttachmentComposer";
import { DefaultToolCallRenderer } from "@/components/tooling/DefaultToolCallRenderer";
import { ImageToolOutputRenderer } from "@/components/tooling/ImageToolOutputRenderer";
import { ProductResultsToolRenderer } from "@/components/tooling/ProductResultsToolRenderer";
import type { AttachmentRef, PendingAttachment } from "@/lib/attachments";
import { upsertToolCall } from "@/lib/toolEvents";
import type { ToolCallEntry } from "@/lib/toolEvents";

type Scenario = "success" | "disconnect" | "send_fail_once";

type Product = {
  id: string;
  name: string;
};

function parseProducts(result: unknown): Product[] | null {
  if (typeof result !== "object" || result === null || !("products" in result)) {
    return null;
  }
  const { products } = result as { products: unknown };
  if (!Array.isArray(products)) {
    return null;
  }
  const parsed = products.filter((item): item is Product => {
    return (
      typeof item === "object" &&
      item !== null &&
      "id" in item &&
      "name" in item &&
      typeof item.id === "string" &&
      typeof item.name === "string"
    );
  });
  return parsed;
}

function parseImageToolOutput(
  result: unknown,
): { caption: string; images: AttachmentRef[] } | null {
  if (typeof result !== "object" || result === null) {
    return null;
  }
  if (!("caption" in result) || !("images" in result)) {
    return null;
  }
  const caption = (result as { caption: unknown }).caption;
  const images = (result as { images: unknown }).images;
  if (typeof caption !== "string" || !Array.isArray(images)) {
    return null;
  }
  const parsedImages = images.filter((image): image is AttachmentRef => {
    return (
      typeof image === "object" &&
      image !== null &&
      "attachment_id" in image &&
      "mime_type" in image &&
      "uri" in image &&
      typeof image.attachment_id === "string" &&
      typeof image.mime_type === "string" &&
      typeof image.uri === "string"
    );
  });
  return {
    caption,
    images: parsedImages,
  };
}

function parseSseChunk(
  chunk: string,
): Array<{ event: string; data: Record<string, unknown> }> {
  const entries = chunk
    .split("\n\n")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);

  return entries.map((entry) => {
    const lines = entry.split("\n");
    const eventLine = lines.find((line) => line.startsWith("event: "));
    const dataLine = lines.find((line) => line.startsWith("data: "));
    return {
      event: eventLine?.slice("event: ".length) ?? "message",
      data: JSON.parse(dataLine?.slice("data: ".length) ?? "{}") as Record<
        string,
        unknown
      >,
    };
  });
}

export default function Home(): ReactElement {
  const [prompt, setPrompt] = useState<string>("Find me storage for a small bedroom");
  const [scenario, setScenario] = useState<Scenario>("success");
  const [assistantText, setAssistantText] = useState<string>("");
  const [toolCallsById, setToolCallsById] = useState<Record<string, ToolCallEntry>>({});
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [lastSendKey, setLastSendKey] = useState<string>("");
  const attachmentFilesRef = useRef<Record<string, File>>({});

  const pendingUploads = attachments.some((attachment) => attachment.status === "uploading");

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
          ? { ...attachment, status: "ready", progress: 100, attachmentRef }
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
              const { errorMessage: _errorMessage, ...rest } = attachment;
              return {
                ...rest,
                status: "uploading" as const,
                progress: 0,
              };
            })()
          : attachment,
      ),
    );
    void uploadAttachment(localId, file);
  };

  const runStream = async (nextScenario: Scenario, sendKey: string): Promise<void> => {
    setAssistantText("");
    setToolCallsById({});
    setError("");
    setIsRunning(true);

    let sawDone = false;
    try {
      const readyAttachments = attachments
        .filter((attachment) => attachment.status === "ready" && attachment.attachmentRef)
        .map((attachment) => attachment.attachmentRef as AttachmentRef);
      const response = await fetch(`/api/mock-agui?scenario=${nextScenario}`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-send-key": sendKey,
        },
        body: JSON.stringify({
          prompt,
          attachments: readyAttachments,
        }),
      });
      if (!response.ok || !response.body) {
        const errorBody = await response.text();
        throw new Error(
          `Request failed with status ${response.status}: ${errorBody || "No response body."}`,
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        const messages = parseSseChunk(parts.join("\n\n"));
        for (const message of messages) {
          if (message.event === "assistant_delta") {
            const textValue = message.data.text;
            if (typeof textValue === "string") {
              setAssistantText((previous) => previous + textValue);
            }
          }
          if (message.event === "tool_status") {
            const toolCallId = message.data.tool_call_id;
            const toolName = message.data.tool;
            const status = message.data.status;
            if (
              typeof toolCallId === "string" &&
              typeof toolName === "string" &&
              (status === "queued" ||
                status === "executing" ||
                status === "complete" ||
                status === "failed")
            ) {
              setToolCallsById((current) =>
                upsertToolCall(current, {
                  tool_call_id: toolCallId,
                  tool: toolName,
                  status,
                  result: message.data.result,
                  errorMessage:
                    typeof message.data.errorMessage === "string"
                      ? message.data.errorMessage
                      : undefined,
                }),
              );
            }
          }
          if (message.event === "done") {
            sawDone = true;
          }
        }
      }

      if (!sawDone) {
        throw new Error("Stream ended unexpectedly before done event.");
      }
    } catch (streamError) {
      const message =
        streamError instanceof Error ? streamError.message : "Streaming failed.";
      setError(message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (pendingUploads) {
      setError("Finish uploading or remove attachments to send.");
      return;
    }
    const sendKey = crypto.randomUUID();
    setLastSendKey(sendKey);
    await runStream(scenario, sendKey);
  };

  const handleRetry = async (): Promise<void> => {
    if (!lastSendKey) {
      return;
    }
    const retryScenario = scenario === "disconnect" ? "success" : scenario;
    await runStream(retryScenario, lastSendKey);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 p-8">
      <h1 className="text-2xl font-semibold">AG-UI Streaming Harness</h1>
      <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
        <label className="flex flex-col gap-1 text-sm">
          Prompt
          <input
            data-testid="prompt-input"
            className="rounded border p-2"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Scenario
          <select
            data-testid="scenario-select"
            className="rounded border p-2"
            value={scenario}
            onChange={(event) => setScenario(event.target.value as Scenario)}
          >
            <option value="success">success</option>
            <option value="disconnect">disconnect</option>
            <option value="send_fail_once">send_fail_once</option>
          </select>
        </label>
        <button
          data-testid="send-button"
          className="w-fit rounded bg-black px-4 py-2 text-white disabled:opacity-60"
          disabled={isRunning || pendingUploads}
          type="submit"
        >
          Send
        </button>
      </form>
      <AttachmentComposer
        attachments={attachments}
        onFilesSelected={handleFilesSelected}
        onRemoveAttachment={handleRemoveAttachment}
        onRetryAttachment={handleRetryAttachment}
      />
      {pendingUploads ? (
        <p className="text-sm text-amber-700" data-testid="pending-upload-warning">
          Finish uploading or remove attachments to send.
        </p>
      ) : null}
      <section className="rounded border p-3">
        <h2 className="text-sm font-medium">Assistant Stream</h2>
        <p data-testid="assistant-text">{assistantText}</p>
        <p data-testid="tool-status">
          Tool status:{" "}
          {Object.values(toolCallsById)
            .map((toolCall) => toolCall.status)
            .join(", ") || "idle"}
        </p>
        <div className="mt-2 space-y-2" data-testid="tool-calls">
          {Object.values(toolCallsById).map((toolCall) => (
            <div className="rounded border p-2" key={toolCall.id}>
              <DefaultToolCallRenderer
                name={toolCall.name}
                status={toolCall.status}
                result={toolCall.result}
                errorMessage={toolCall.errorMessage}
              />
              {toolCall.name === "run_search_graph" && toolCall.status === "complete" ? (
                <ProductResultsToolRenderer
                  products={parseProducts(toolCall.result) ?? []}
                />
              ) : null}
              {toolCall.name === "generate_floor_plan_preview" &&
              toolCall.status === "complete" ? (
                (() => {
                  const imageOutput = parseImageToolOutput(toolCall.result);
                  return imageOutput ? (
                    <ImageToolOutputRenderer
                      caption={imageOutput.caption}
                      images={imageOutput.images}
                    />
                  ) : null;
                })()
              ) : null}
            </div>
          ))}
        </div>
      </section>
      {error ? (
        <section className="rounded border border-red-500 bg-red-50 p-3">
          <p data-testid="stream-error">Stream error: {error}</p>
          <button
            data-testid="retry-button"
            className="mt-2 rounded border border-red-500 px-3 py-1"
            onClick={handleRetry}
            type="button"
          >
            Retry
          </button>
        </section>
      ) : null}
    </main>
  );
}
