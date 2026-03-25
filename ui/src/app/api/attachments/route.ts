import { NextRequest, NextResponse } from "next/server";

import { logServerRouteEvent } from "@/lib/serverRouteLogging";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";
const uploadUrl = new URL("../attachments", agUiUrl).toString();

export const POST = async (request: NextRequest): Promise<Response> => {
  const body = await request.arrayBuffer();
  const contentType = request.headers.get("content-type") ?? "application/octet-stream";
  const fileName = request.headers.get("x-filename");
  const roomId = request.headers.get("x-room-id")?.trim() ?? "";
  const threadId = request.headers.get("x-thread-id")?.trim() ?? "";
  const runId = request.headers.get("x-run-id");
  const useMockAgent = process.env.NEXT_PUBLIC_USE_MOCK_AGENT === "1";

  if (useMockAgent) {
    await new Promise((resolve) => {
      setTimeout(resolve, 250);
    });
    return NextResponse.json({
      attachment_id: crypto.randomUUID(),
      mime_type: contentType,
      uri: "/attachments/mock",
      width: null,
      height: null,
      file_name: fileName ?? null,
    });
  }

  let response: Response;
  try {
    response = await fetch(uploadUrl, {
      method: "POST",
      headers: {
        "content-type": contentType,
        ...(fileName ? { "x-filename": fileName } : {}),
        ...(roomId ? { "x-room-id": roomId } : {}),
        ...(threadId ? { "x-thread-id": threadId } : {}),
        ...(runId ? { "x-run-id": runId } : {}),
      },
      body,
    });
  } catch (error) {
    logServerRouteEvent("error", "ui_attachment_upload_upstream_unreachable", {
      detail: error instanceof Error ? error.message : "Unknown attachment upload failure.",
      route: "/api/attachments",
      room_id: roomId || null,
      run_id: runId,
      thread_id: threadId || null,
    });
    throw error;
  }

  const text = await response.text();
  if (!response.ok) {
    logServerRouteEvent("error", "ui_attachment_upload_failed", {
      route: "/api/attachments",
      room_id: roomId || null,
      run_id: runId,
      status_code: response.status,
      thread_id: threadId || null,
    });
  }
  return new Response(text, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
};
