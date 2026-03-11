import { NextRequest } from "next/server";

import { handleCopilotKitRequest } from "./handler";

export const GET = async (request: NextRequest): Promise<Response> => {
  return handleCopilotKitRequest(request);
};

export const POST = async (request: NextRequest): Promise<Response> => {
  return handleCopilotKitRequest(request);
};
