"use client";

import { FormEvent, useState } from "react";
import type { ReactElement } from "react";

type Scenario = "success" | "disconnect";
type ToolState = "idle" | "executing" | "complete" | "failed";

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
  const [toolState, setToolState] = useState<ToolState>("idle");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const runStream = async (nextScenario: Scenario): Promise<void> => {
    setAssistantText("");
    setToolState("idle");
    setError("");
    setIsRunning(true);

    let sawDone = false;
    try {
      const response = await fetch(`/api/mock-agui?scenario=${nextScenario}`);
      if (!response.ok || !response.body) {
        throw new Error(`Request failed with status ${response.status}`);
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
            const status = message.data.status;
            if (status === "executing" || status === "complete") {
              setToolState(status);
            }
          }
          if (message.event === "done") {
            sawDone = true;
          }
        }
      }

      if (!sawDone) {
        setToolState("failed");
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
    await runStream(scenario);
  };

  const handleRetry = async (): Promise<void> => {
    await runStream("success");
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
          </select>
        </label>
        <button
          data-testid="send-button"
          className="w-fit rounded bg-black px-4 py-2 text-white disabled:opacity-60"
          disabled={isRunning}
          type="submit"
        >
          Send
        </button>
      </form>
      <section className="rounded border p-3">
        <h2 className="text-sm font-medium">Assistant Stream</h2>
        <p data-testid="assistant-text">{assistantText}</p>
        <p data-testid="tool-status">Tool status: {toolState}</p>
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
