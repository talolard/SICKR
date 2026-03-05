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
      });
      await sleep(80);

      if (scenario === "disconnect") {
        controller.close();
        return;
      }

      push("tool_status", {
        tool_call_id: "tool-1",
        tool: "run_search_graph",
        status: "complete",
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
