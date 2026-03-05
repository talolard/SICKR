import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ attachment_id: string }> },
): Promise<Response> {
  const params = await context.params;
  const upstreamUrl = new URL(`../attachments/${params.attachment_id}`, agUiUrl).toString();
  const response = await fetch(upstreamUrl, {
    method: "GET",
  });
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

