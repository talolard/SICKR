import { NextRequest } from "next/server";

import { handleCopilotKitRequest } from "../handler";

export const POST = async (request: NextRequest): Promise<Response> => {
  return handleCopilotKitRequest(request);
};

