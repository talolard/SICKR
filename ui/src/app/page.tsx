"use client";

import { FormEvent, useState } from "react";
import type { ReactElement } from "react";
import { DefaultToolCallRenderer } from "@/components/tooling/DefaultToolCallRenderer";
import { ProductResultsToolRenderer } from "@/components/tooling/ProductResultsToolRenderer";
import { upsertToolCall } from "@/lib/toolEvents";
import type { ToolCallEntry } from "@/lib/toolEvents";

type Scenario = "success" | "disconnect";

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
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const runStream = async (nextScenario: Scenario): Promise<void> => {
    setAssistantText("");
    setToolCallsById({});
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
