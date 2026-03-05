import { HttpAgent } from "@ag-ui/client";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();
const agUiUrl = process.env.PY_AG_UI_URL ?? "http://localhost:8000/ag-ui";

const runtime = new CopilotRuntime({
  agents: {
    ikea_agent: new HttpAgent({ url: agUiUrl }),
  },
});

export const POST = async (request: NextRequest): Promise<Response> => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(request);
};
