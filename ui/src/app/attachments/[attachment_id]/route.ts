import { NextRequest } from "next/server";

import { logServerRouteEvent } from "@/lib/serverRouteLogging";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ attachment_id: string }> },
): Promise<Response> {
  const params = await context.params;
  const upstreamUrl = new URL(`../attachments/${params.attachment_id}`, agUiUrl).toString();
  let response: Response;
  try {
    response = await fetch(upstreamUrl, {
      method: "GET",
    });
  } catch (error) {
    logServerRouteEvent("error", "ui_attachment_read_upstream_unreachable", {
      attachment_id: params.attachment_id,
      detail: error instanceof Error ? error.message : "Unknown attachment read failure.",
      route: "/attachments/[attachment_id]",
    });
    throw error;
  }
  if (!response.ok) {
    logServerRouteEvent("error", "ui_attachment_read_failed", {
      attachment_id: params.attachment_id,
      route: "/attachments/[attachment_id]",
      status_code: response.status,
    });
  }
  const body = await response.arrayBuffer();
  return new Response(body, {
    status: response.status,
    headers: {
      "content-type":
        response.headers.get("content-type") ?? "application/octet-stream",
      "cache-control": response.headers.get("cache-control") ?? "private, max-age=60",
    },
  });
}
