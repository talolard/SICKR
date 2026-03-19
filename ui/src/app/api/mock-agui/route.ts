import { NextRequest } from "next/server";

const encoder = new TextEncoder();
const failedSendKeys = new Set<string>();

function formatEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

export async function GET(request: NextRequest): Promise<Response> {
  return handleStreamRequest(request, { prompt: "", attachments: [] });
}

type MockRunInput = {
  prompt: string;
  attachments: Array<{ attachment_id: string; uri: string }>;
};

async function handleStreamRequest(
  request: NextRequest,
  runInput: MockRunInput,
): Promise<Response> {
  const scenario = request.nextUrl.searchParams.get("scenario") ?? "success";
  const sendKey = request.headers.get("x-send-key") ?? "default";

  if (scenario === "send_fail_once" && !failedSendKeys.has(sendKey)) {
    failedSendKeys.add(sendKey);
    return new Response(
      JSON.stringify({
        detail: "Temporary upstream send failure. Retry to reuse uploaded attachments.",
      }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }

  const hasExpiredRef = runInput.attachments.some((attachment) =>
    attachment.uri.includes("expired"),
  );
  if (hasExpiredRef) {
    return new Response(
      JSON.stringify({ detail: "Attachment reference expired. Please re-upload." }),
      { status: 410, headers: { "content-type": "application/json" } },
    );
  }

  const stream = new ReadableStream({
    async start(controller) {
      const push = (event: string, data: unknown): void => {
        controller.enqueue(encoder.encode(formatEvent(event, data)));
      };

      push("assistant_delta", { text: "Analyzing request..." });
      await sleep(80);
      if (runInput.attachments.length > 0) {
        push("assistant_delta", {
          text: ` Using ${runInput.attachments.length} uploaded image(s).`,
        });
      }
      await sleep(80);
      push("tool_status", {
        tool_call_id: "tool-1",
        tool: "run_search_graph",
        status: "executing",
        args: {
          queries: [
            {
              query_id: "query-1",
              semantic_query: runInput.prompt,
            },
          ],
        },
      });
      if (scenario === "long_running") {
        push("progress", {
          tool_call_id: "tool-1",
          percent: 10,
          label: "Searching catalog",
        });
        await sleep(300);
        push("progress", {
          tool_call_id: "tool-1",
          percent: 45,
          label: "Searching catalog",
        });
        await sleep(300);
        push("progress", {
          tool_call_id: "tool-1",
          percent: 80,
          label: "Ranking matches",
        });
        await sleep(300);
      } else {
        await sleep(80);
      }

      if (scenario === "disconnect") {
        push("error", {
          message: "Stream ended unexpectedly before done event.",
        });
        await sleep(80);
        controller.close();
        return;
      }

      push("tool_status", {
        tool_call_id: "tool-1",
        tool: "run_search_graph",
        status: "complete",
        args: {
          queries: [
            {
              query_id: "query-1",
              semantic_query: runInput.prompt,
            },
          ],
        },
        result: {
          products: [
            {
              id: "prod-001",
              name: "BRIMNES Wardrobe",
            },
          ],
        },
      });
      await sleep(80);
      push("tool_status", {
        tool_call_id: "tool-2",
        tool: "generate_floor_plan_preview",
        status: "complete",
        result: {
          caption: "Draft floor plan preview",
          images: [
            {
              attachment_id: "generated-1",
              mime_type: "image/svg+xml",
              uri: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='120'%3E%3Crect width='220' height='120' fill='%23f6f6f6'/%3E%3Crect x='15' y='20' width='70' height='70' fill='%2393c5fd'/%3E%3Crect x='105' y='30' width='95' height='50' fill='%23fdba74'/%3E%3C/svg%3E",
              width: 220,
              height: 120,
              file_name: "floor-plan.svg",
            },
          ],
        },
      });
      push("progress", {
        tool_call_id: "tool-2",
        percent: 100,
        label: "Floor plan ready",
      });
      await sleep(80);
      push("assistant_delta", { text: " Found 3 matching products." });
      push("done", { ok: true });
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}

export async function POST(request: NextRequest): Promise<Response> {
  const body = (await request.json()) as MockRunInput;
  return handleStreamRequest(request, body);
}
