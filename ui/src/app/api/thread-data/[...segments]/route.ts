import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(segments: string[], queryString: string): string {
  const joined = segments.join("/");
  const upstream = new URL(`../api/${joined}${queryString}`, agUiUrl);
  return upstream.toString();
}

async function proxyRequest(
  request: NextRequest,
  params: { segments: string[] },
): Promise<Response> {
  const query = request.nextUrl.search ? request.nextUrl.search : "";
  const upstreamUrl = buildUpstreamUrl(params.segments, query);
  const body = request.method === "PATCH" ? await request.text() : null;
  const upstreamResponse = await fetch(upstreamUrl, {
    method: request.method,
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/json",
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

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ segments: string[] }> },
): Promise<Response> {
  return await proxyRequest(request, await params);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ segments: string[] }> },
): Promise<Response> {
  return await proxyRequest(request, await params);
}
