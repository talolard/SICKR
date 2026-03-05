import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const encoder = new TextEncoder();
const baseAgUiUrl = process.env.PY_AG_UI_URL ?? "http://127.0.0.1:8000/ag-ui/";
const agUiUrl = baseAgUiUrl.endsWith("/") ? baseAgUiUrl : `${baseAgUiUrl}/`;

type RunRequest = {
  prompt: string;
  attachments?: Array<{ attachment_id: string; uri: string }>;
};

function formatEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

export const POST = async (request: NextRequest): Promise<Response> => {
  const body = (await request.json()) as RunRequest;
  const stream = new ReadableStream({
    async start(controller) {
      const push = (event: string, data: unknown): void => {
        controller.enqueue(encoder.encode(formatEvent(event, data)));
      };

      try {
        const agent = new HttpAgent({ url: agUiUrl });
        agent.addMessage({
          id: crypto.randomUUID(),
          role: "user",
          content: body.prompt,
        });
        await agent.runAgent(undefined, {
          onTextMessageContentEvent: (params: any) => {
            push("assistant_delta", { text: params.event.delta });
          },
          onToolCallStartEvent: (params: any) => {
            push("tool_status", {
              tool_call_id: params.event.toolCallId,
              tool: params.event.toolCallName,
              status: "executing",
              args: params.event.toolCallArgs ?? params.toolCallArgs,
            });
          },
          onToolCallResultEvent: (params: any) => {
            push("tool_result", {
              tool_call_id: params.event.toolCallId,
              result: params.event.result ?? params.event.content,
            });
          },
          onToolCallEndEvent: (params: any) => {
            push("tool_status", {
              tool_call_id: params.event.toolCallId,
              tool: params.toolCallName,
              status: "complete",
              args: params.event.toolCallArgs ?? params.toolCallArgs,
            });
          },
          onRunErrorEvent: (params: any) => {
            push("error", { message: params.event.message });
          },
        });
        push("done", { ok: true });
      } catch (error) {
        const message = error instanceof Error ? error.message : "AG-UI run failed.";
        push("error", { message });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
};
