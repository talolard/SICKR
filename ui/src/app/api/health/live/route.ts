import { liveHealthResponse } from "../shared";

export async function GET(): Promise<Response> {
  return liveHealthResponse();
}
