"use client";

import { FormEvent, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ReactElement } from "react";
import { AttachmentComposer } from "@/components/attachments/AttachmentComposer";
import { RunStatusContainer } from "@/components/containers/RunStatusContainer";
import { ThreadContainer } from "@/components/containers/ThreadContainer";
import { DefaultToolCallRenderer } from "@/components/tooling/DefaultToolCallRenderer";
import { ImageToolOutputRenderer } from "@/components/tooling/ImageToolOutputRenderer";
import type { AttachmentRef, PendingAttachment } from "@/lib/attachments";
import { upsertToolCall } from "@/lib/toolEvents";
import type { ToolCallEntry } from "@/lib/toolEvents";
import {
  loadActiveThreadId,
  loadThreadSnapshot,
  saveActiveThreadId,
  saveThreadSnapshot,
} from "@/lib/threadStore";

type Scenario = "success" | "disconnect" | "send_fail_once" | "long_running";
type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  toolCallIds: string[];
};

const useMockAgent = process.env.NEXT_PUBLIC_USE_MOCK_AGENT !== "0";

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

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

export default function Home(): ReactElement {
  const [useMockMode, setUseMockMode] = useState<boolean>(useMockAgent);
  const [prompt, setPrompt] = useState<string>("Find me storage for a small bedroom");
  const [scenario, setScenario] = useState<Scenario>("success");
  const [assistantText, setAssistantText] = useState<string>("");
  const [toolCallsById, setToolCallsById] = useState<Record<string, ToolCallEntry>>({});
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [lastSendKey, setLastSendKey] = useState<string>("");
  const [toolProgressById, setToolProgressById] = useState<
    Record<string, { percent: number; label: string }>
  >({});
  const [threadId, setThreadId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isBootstrapped, setIsBootstrapped] = useState<boolean>(false);
  const attachmentFilesRef = useRef<Record<string, File>>({});
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeAssistantMessageIdRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    const url = new URL(window.location.href);
    const mockParam = url.searchParams.get("mock");
    if (mockParam === "1") {
      setUseMockMode(true);
    } else if (mockParam === "0") {
      setUseMockMode(false);
    }
    const threadFromUrl = url.searchParams.get("thread");
    const resolvedThreadId =
      threadFromUrl ?? loadActiveThreadId() ?? crypto.randomUUID().slice(0, 8);
    setThreadId(resolvedThreadId);
    saveActiveThreadId(resolvedThreadId);
    const snapshot = loadThreadSnapshot(resolvedThreadId);
    if (snapshot) {
      setPrompt(snapshot.prompt);
      setAssistantText(snapshot.assistantText);
      setToolCallsById(snapshot.toolCallsById);
      setAttachments(snapshot.attachments);
      setMessages(snapshot.messages ?? []);
    }
    url.searchParams.set("thread", resolvedThreadId);
    window.history.replaceState({}, "", url.toString());
    setIsBootstrapped(true);
  }, []);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    saveThreadSnapshot({
      threadId,
      prompt,
      assistantText,
      toolCallsById,
      attachments,
      messages,
    });
  }, [assistantText, attachments, messages, prompt, threadId, toolCallsById]);

  const pendingUploads = attachments.some((attachment) => attachment.status === "uploading");

  const attachToolCallToActiveAssistant = (toolCallId: string): void => {
    const activeId = activeAssistantMessageIdRef.current;
    if (!activeId) {
      return;
    }
    setMessages((current) =>
      current.map((message) =>
        message.id === activeId && !message.toolCallIds.includes(toolCallId)
          ? { ...message, toolCallIds: [...message.toolCallIds, toolCallId] }
          : message,
      ),
    );
  };

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
    if (useMockMode) {
      await sleep(150);
      setAttachmentProgress(localId, 28);
      await sleep(250);
      setAttachmentProgress(localId, 61);
      await sleep(250);
      setAttachmentReady(localId, {
        attachment_id: crypto.randomUUID(),
        mime_type: file.type || "application/octet-stream",
        uri: "/attachments/mock",
        width: null,
        height: null,
        file_name: file.name,
      });
      return;
    }

    await new Promise<void>((resolve, reject) => {
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
        setTimeout(() => {
          void uploadAttachment(attachment.localId, file);
        }, 0);
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

  const runStream = async (nextScenario: Scenario, sendKey: string): Promise<void> => {
    setAssistantText("");
    setError("");
    setIsRunning(true);
    setToolProgressById({});
    const controller = new AbortController();
    abortControllerRef.current = controller;

    let sawDone = false;
    try {
      const readyAttachments = attachments
        .filter((attachment) => attachment.status === "ready" && attachment.attachmentRef)
        .map((attachment) => attachment.attachmentRef as AttachmentRef);
      const endpoint = useMockMode
        ? `/api/mock-agui?scenario=${nextScenario}`
        : "/api/agui-run";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(useMockMode ? { "x-send-key": sendKey } : {}),
        },
        body: JSON.stringify({
          prompt,
          attachments: readyAttachments,
        }),
        signal: controller.signal,
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
              const activeAssistantId = activeAssistantMessageIdRef.current;
              if (activeAssistantId) {
                setMessages((current) =>
                  current.map((messageEntry) =>
                    messageEntry.id === activeAssistantId
                      ? { ...messageEntry, text: `${messageEntry.text}${textValue}` }
                      : messageEntry,
                  ),
                );
              }
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
              attachToolCallToActiveAssistant(toolCallId);
              setToolCallsById((current) =>
                upsertToolCall(current, {
                  tool_call_id: toolCallId,
                  tool: toolName,
                  status,
                  result: message.data.result,
                  args: message.data.args,
                  errorMessage:
                    typeof message.data.errorMessage === "string"
                      ? message.data.errorMessage
                      : undefined,
                }),
              );
              if (status === "executing") {
                setToolProgressById((current) =>
                  current[toolCallId]
                    ? current
                    : {
                        ...current,
                        [toolCallId]: {
                          percent: 0,
                          label:
                            toolName === "run_search_graph" ? "Searching catalog" : "Working",
                        },
                      },
                );
              }
            }
          }
          if (message.event === "tool_result") {
            const toolCallId = message.data.tool_call_id;
            if (typeof toolCallId === "string") {
              attachToolCallToActiveAssistant(toolCallId);
              setToolCallsById((current) => {
                const existing = current[toolCallId];
                if (!existing) {
                  return current;
                }
                return upsertToolCall(current, {
                  tool_call_id: toolCallId,
                  tool: existing.name,
                  status: existing.status,
                  result: message.data.result,
                  args: existing.args,
                  errorMessage: undefined,
                });
              });
            }
          }
          if (message.event === "progress") {
            const toolCallId = message.data.tool_call_id;
            const percent = message.data.percent;
            const label = message.data.label;
            if (
              typeof toolCallId === "string" &&
              typeof percent === "number" &&
              typeof label === "string"
            ) {
              setToolProgressById((current) => ({
                ...current,
                [toolCallId]: { percent, label },
              }));
            }
          }
          if (message.event === "done") {
            sawDone = true;
          }
          if (message.event === "error") {
            const errorMessage = message.data.message;
            throw new Error(
              typeof errorMessage === "string" ? errorMessage : "Streaming failed.",
            );
          }
        }
      }

      if (!sawDone) {
        throw new Error("Stream ended unexpectedly before done event.");
      }
    } catch (streamError) {
      const message =
        streamError instanceof Error && streamError.name === "AbortError"
          ? "Run canceled locally."
          : streamError instanceof Error
            ? streamError.message
            : "Streaming failed.";
      setError(message);
    } finally {
      abortControllerRef.current = null;
      activeAssistantMessageIdRef.current = null;
      setIsRunning(false);
    }
  };

  const handleCancelRun = (): void => {
    abortControllerRef.current?.abort();
  };

  const handleNewThread = (): void => {
    const nextThreadId = crypto.randomUUID().slice(0, 8);
    setThreadId(nextThreadId);
    setPrompt("Find me storage for a small bedroom");
    setAssistantText("");
    setToolCallsById({});
    setMessages([]);
    setAttachments([]);
    setError("");
    setToolProgressById({});
    activeAssistantMessageIdRef.current = null;
    saveActiveThreadId(nextThreadId);
    const url = new URL(window.location.href);
    url.searchParams.set("thread", nextThreadId);
    window.history.replaceState({}, "", url.toString());
  };

  const handleSubmit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (pendingUploads) {
      setError("Finish uploading or remove attachments to send.");
      return;
    }
    const assistantMessageId = crypto.randomUUID();
    activeAssistantMessageIdRef.current = assistantMessageId;
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        text: prompt,
        toolCallIds: [],
      },
      {
        id: assistantMessageId,
        role: "assistant",
        text: "",
        toolCallIds: [],
      },
    ]);
    const sendKey = crypto.randomUUID();
    setLastSendKey(sendKey);
    await runStream(scenario, sendKey);
  };

  const handleRetry = async (): Promise<void> => {
    if (!lastSendKey) {
      return;
    }
    const assistantMessageId = crypto.randomUUID();
    activeAssistantMessageIdRef.current = assistantMessageId;
    setMessages((current) => [
      ...current,
      {
        id: assistantMessageId,
        role: "assistant",
        text: "",
        toolCallIds: [],
      },
    ]);
    const retryScenario =
      useMockMode && scenario === "disconnect" ? "success" : scenario;
    await runStream(retryScenario, lastSendKey);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-4 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">AG-UI Streaming Harness</h1>
        <span
          className={`rounded px-2 py-1 text-xs font-semibold ${
            useMockMode ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
          }`}
          data-testid="mode-badge"
        >
          {useMockMode ? "MOCK MODE" : "REAL MODE"}
        </span>
      </div>
      {threadId ? (
        <ThreadContainer onNewThread={handleNewThread} threadId={threadId} />
      ) : null}
      <section className="flex min-h-[360px] flex-col gap-4 rounded border bg-white p-4">
        <h2 className="text-sm font-medium text-gray-700">Chat</h2>
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded border bg-gray-50 p-3">
          {!isBootstrapped ? (
            <p className="text-sm text-gray-500">Preparing thread session...</p>
          ) : messages.length === 0 ? (
            <p className="text-sm text-gray-500">Start by sending a message.</p>
          ) : null}
          {isBootstrapped
            ? messages.map((message) => (
            <article
              className={`max-w-[85%] rounded px-3 py-2 ${
                message.role === "user"
                  ? "ml-auto bg-black text-white"
                  : "mr-auto border bg-white text-black"
              }`}
              key={message.id}
            >
              <p className="text-xs opacity-70">{message.role === "user" ? "You" : "Assistant"}</p>
              <p className="whitespace-pre-wrap text-sm">{message.text}</p>
              {message.role === "assistant" ? (
                <div className="mt-2 space-y-2">
                  {message.toolCallIds.map((toolCallId) => {
                    const toolCall = toolCallsById[toolCallId];
                    if (!toolCall) {
                      return null;
                    }
                    return (
                      <div className="rounded border p-2" key={toolCall.id}>
                        <DefaultToolCallRenderer
                          name={toolCall.name}
                          status={toolCall.status}
                          result={toolCall.result}
                          args={toolCall.args}
                          errorMessage={toolCall.errorMessage}
                        />
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
                    );
                  })}
                </div>
              ) : null}
            </article>
              ))
            : null}
        </div>
      </section>
      {isBootstrapped ? (
        <form className="flex flex-col gap-3 rounded border bg-white p-4" onSubmit={handleSubmit}>
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
          {useMockMode ? (
            <select
              data-testid="scenario-select"
              className="rounded border p-2"
              value={scenario}
              onChange={(event) => setScenario(event.target.value as Scenario)}
            >
              <option value="success">success</option>
              <option value="disconnect">disconnect</option>
              <option value="send_fail_once">send_fail_once</option>
              <option value="long_running">long_running</option>
            </select>
          ) : (
            <p className="rounded border p-2 text-sm text-gray-700">
              Real backend mode (`/api/agui-run`)
            </p>
          )}
        </label>
        <div className="flex items-center gap-2">
          <button
            data-testid="send-button"
            className="w-fit rounded bg-black px-4 py-2 text-white disabled:opacity-60"
            disabled={isRunning || pendingUploads}
            type="submit"
          >
            Send
          </button>
          <button
            className="w-fit rounded border px-4 py-2 disabled:opacity-60"
            data-testid="cancel-button"
            disabled={!isRunning}
            onClick={handleCancelRun}
            type="button"
          >
            Cancel run
          </button>
        </div>
        </form>
      ) : (
        <section
          className="rounded border bg-white p-4 text-sm text-gray-500"
          data-testid="bootstrap-loading"
        >
          Preparing controls...
        </section>
      )}
      {isBootstrapped ? (
        <RunStatusContainer
          isRunning={isRunning}
          runningToolCount={
            Object.values(toolCallsById).filter((toolCall) => toolCall.status === "executing")
              .length
          }
          toolProgressById={toolProgressById}
        />
      ) : null}
      {isBootstrapped ? (
        <AttachmentComposer
          attachments={attachments}
          onFilesSelected={handleFilesSelected}
          onRemoveAttachment={handleRemoveAttachment}
          onRetryAttachment={handleRetryAttachment}
        />
      ) : null}
      {isBootstrapped && pendingUploads ? (
        <p className="text-sm text-amber-700" data-testid="pending-upload-warning">
          Finish uploading or remove attachments to send.
        </p>
      ) : null}
      <p className="hidden" data-testid="assistant-text">
        {assistantText}
      </p>
      <p className="hidden" data-testid="tool-status">
        Tool status:{" "}
        {Object.values(toolCallsById)
          .map((toolCall) => toolCall.status)
          .join(", ") || "idle"}
      </p>
      <div className="hidden" data-testid="tool-calls" />
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
