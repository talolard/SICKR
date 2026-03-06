import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function upstreamUrl(threadId: string): string {
  return new URL(`../api/threads/${threadId}/room-3d-assets`, agUiUrl).toString();
}

async function proxy(request: NextRequest): Promise<Response> {
  const threadId = request.headers.get("x-thread-id");
  if (!threadId) {
    return Response.json(
      { detail: "Missing required x-thread-id header." },
      { status: 400 },
    );
  }
  const runId = request.headers.get("x-run-id");
  const body = request.method === "POST" ? await request.text() : null;

  const upstreamResponse = await fetch(upstreamUrl(threadId), {
    method: request.method,
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
      ...(runId ? { "x-run-id": runId } : {}),
    },
    body,
  });

  const text = await upstreamResponse.text();
  return new Response(text, {
    status: upstreamResponse.status,
    headers: {
      "content-type": upstreamResponse.headers.get("content-type") ?? "application/json",
    },
  });
}

export async function GET(request: NextRequest): Promise<Response> {
  return await proxy(request);
}

export async function POST(request: NextRequest): Promise<Response> {
  return await proxy(request);
}
