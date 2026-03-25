import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(request: NextRequest): string {
  const baseUrl = new URL("../", agUiUrl);
  const upstream = new URL("api/health", baseUrl);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }
  return upstream.toString();
}

export async function GET(request: NextRequest): Promise<Response> {
  try {
    const upstreamResponse = await fetch(buildUpstreamUrl(request), {
      method: "GET",
      headers: { accept: "application/json" },
      cache: "no-store",
    });

    const text = await upstreamResponse.text();
    return new Response(text, {
      status: upstreamResponse.status,
      headers: {
        "content-type": upstreamResponse.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown backend health error.";
    return new Response(
      JSON.stringify({
        status: "not_ready",
        checks: {
          backend: {
            status: "failed",
            detail: `UI readiness proxy could not reach backend health route: ${detail}`,
          },
        },
      }),
      {
        status: 503,
        headers: {
          "content-type": "application/json",
          "cache-control": "no-store",
        },
      },
    );
  }
}
