import { NextRequest, NextResponse } from "next/server";

import { logServerRouteEvent } from "@/lib/serverRouteLogging";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";
const uploadUrl = new URL("../attachments", agUiUrl).toString();

export const POST = async (request: NextRequest): Promise<Response> => {
  const body = await request.arrayBuffer();
  const contentType = request.headers.get("content-type") ?? "application/octet-stream";
  const fileName = request.headers.get("x-filename");
  const threadId = request.headers.get("x-thread-id")?.trim() ?? "";
  const runId = request.headers.get("x-run-id");
  const useMockAgent = process.env.NEXT_PUBLIC_USE_MOCK_AGENT === "1";

  if (!threadId) {
    return new NextResponse(
      "Attachments require a thread id before upload so private artifacts stay thread-scoped.",
      { status: 400, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }

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

  const response = await fetch(uploadUrl, {
    method: "POST",
    headers: {
      "content-type": contentType,
      ...(fileName ? { "x-filename": fileName } : {}),
      "x-thread-id": threadId,
      ...(runId ? { "x-run-id": runId } : {}),
    },
    body,
  });

  const text = await response.text();
  if (!response.ok) {
    logServerRouteEvent("error", "ui_attachment_upload_failed", {
      route: "/api/attachments",
      run_id: runId,
      status_code: response.status,
      thread_id: threadId,
    });
  }
  return new Response(text, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
};
