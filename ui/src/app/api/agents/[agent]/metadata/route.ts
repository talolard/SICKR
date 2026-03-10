import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ agent: string }> },
): Promise<Response> {
  const { agent } = await context.params;
  const baseUrl = new URL("../../", agUiUrl);
  const upstream = new URL(`api/agents/${agent}/metadata`, baseUrl);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }

  const upstreamResponse = await fetch(upstream, {
    method: "GET",
    headers: { accept: "application/json" },
  });

  const body = await upstreamResponse.text();
  return new Response(body, {
    status: upstreamResponse.status,
    headers: { "content-type": "application/json" },
  });
}
