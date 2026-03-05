import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("http://localhost/api/health", () => {
    return HttpResponse.json({ status: "ok" });
  }),
];
