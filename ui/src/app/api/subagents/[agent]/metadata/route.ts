import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(agent: string, request: NextRequest): string {
  const baseUrl = new URL("../", agUiUrl);
  const upstream = new URL(`api/subagents/${agent}/metadata`, baseUrl);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }
  return upstream.toString();
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ agent: string }> },
): Promise<Response> {
  const { agent } = await context.params;
  const upstreamResponse = await fetch(buildUpstreamUrl(agent, request), {
    method: "GET",
    headers: { accept: "application/json" },
  });
  const payload = await upstreamResponse.text();
  return new Response(payload, {
    status: upstreamResponse.status,
    headers: { "content-type": upstreamResponse.headers.get("content-type") ?? "application/json" },
  });
}
