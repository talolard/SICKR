import { NextRequest } from "next/server";

const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui/";
const commentsUrl = new URL("../api/comments", agUiUrl).toString();

export const POST = async (request: NextRequest): Promise<Response> => {
  try {
    const body = await request.text();
    const response = await fetch(commentsUrl, {
      method: "POST",
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json",
      },
      body,
    });
    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unknown proxy failure";
    return Response.json(
      {
        detail,
        upstream: commentsUrl,
      },
      { status: 502 },
    );
  }
};
