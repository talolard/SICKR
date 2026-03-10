import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(agent: string, segments: string[], query: string): string {
  const baseUrl = new URL("../", agUiUrl);
  const joined = segments.join("/");
  const path = joined.length > 0 ? `subagents/${agent}/chat/${joined}` : `subagents/${agent}/chat/`;
  const upstream = new URL(path, baseUrl);
  if (query) {
    upstream.search = query;
  }
  return upstream.toString();
}

async function proxyRequest(
  request: NextRequest,
  params: { agent: string; segments?: string[] },
): Promise<Response> {
  const segments = params.segments ?? [];
  const upstreamUrl = buildUpstreamUrl(
    params.agent,
    segments,
    request.nextUrl.search ? request.nextUrl.search : "",
  );
  const body = request.method === "GET" || request.method === "HEAD" ? null : await request.text();
  const upstreamResponse = await fetch(upstreamUrl, {
    method: request.method,
    headers: {
      accept: request.headers.get("accept") ?? "*/*",
      "content-type": request.headers.get("content-type") ?? "text/plain",
    },
    body,
  });
  const contentType = upstreamResponse.headers.get("content-type") ?? "text/plain; charset=utf-8";
  const payload = await upstreamResponse.arrayBuffer();
  return new Response(payload, {
    status: upstreamResponse.status,
    headers: { "content-type": contentType },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ agent: string; segments?: string[] }> },
): Promise<Response> {
  return proxyRequest(request, await context.params);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ agent: string; segments?: string[] }> },
): Promise<Response> {
  return proxyRequest(request, await context.params);
}
