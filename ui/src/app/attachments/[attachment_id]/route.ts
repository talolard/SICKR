import { NextRequest } from "next/server";

import { backendProxyLogFields, buildBackendProxyUrl } from "@/lib/backendProxy";
import { logServerRouteEvent } from "@/lib/serverRouteLogging";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ attachment_id: string }> },
): Promise<Response> {
  const params = await context.params;
  const upstreamUrl = buildBackendProxyUrl(`/attachments/${params.attachment_id}`);
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
      upstream_url: upstreamUrl.toString(),
      ...backendProxyLogFields(),
    });
    throw error;
  }
  if (!response.ok) {
    logServerRouteEvent("error", "ui_attachment_read_failed", {
      attachment_id: params.attachment_id,
      route: "/attachments/[attachment_id]",
      status_code: response.status,
      upstream_url: upstreamUrl.toString(),
      ...backendProxyLogFields(),
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
