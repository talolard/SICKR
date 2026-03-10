import { NextRequest } from "next/server";

type SubagentItem = {
  name: string;
  description: string;
  web_path: string;
};

type SubagentListResponse = {
  subagents: SubagentItem[];
};

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";

function buildUpstreamUrl(request: NextRequest): string {
  const baseUrl = new URL("../", agUiUrl);
  const upstream = new URL("api/subagents", baseUrl);
  if (request.nextUrl.search) {
    upstream.search = request.nextUrl.search;
  }
  return upstream.toString();
}

export async function GET(request: NextRequest): Promise<Response> {
  const upstreamResponse = await fetch(buildUpstreamUrl(request), {
    method: "GET",
    headers: { accept: "application/json" },
  });

  const baseUrl = new URL("../", agUiUrl);
  const payload = (await upstreamResponse.json()) as SubagentListResponse;
  const shaped = {
    subagents: payload.subagents.map((item) => ({
      ...item,
      chat_proxy_path: `/api/subagents/${item.name}/chat/`,
      chat_url: new URL(item.web_path, baseUrl).toString(),
    })),
  };

  return new Response(JSON.stringify(shaped), {
    status: upstreamResponse.status,
    headers: { "content-type": "application/json" },
  });
}
