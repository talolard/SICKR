import { NextRequest } from "next/server";

import { proxyReadyHealth } from "../shared";

export async function GET(request: NextRequest): Promise<Response> {
  return proxyReadyHealth(request);
}
