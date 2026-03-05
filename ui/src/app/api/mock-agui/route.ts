import { NextRequest } from "next/server";

const encoder = new TextEncoder();

function formatEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}

export async function GET(request: NextRequest): Promise<Response> {
  const scenario = request.nextUrl.searchParams.get("scenario") ?? "success";

  const stream = new ReadableStream({
    async start(controller) {
      const push = (event: string, data: unknown): void => {
        controller.enqueue(encoder.encode(formatEvent(event, data)));
      };

      push("assistant_delta", { text: "Analyzing request..." });
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
