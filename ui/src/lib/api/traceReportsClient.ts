export type TraceReportCreateRequest = {
  title: string;
  description?: string;
  thread_id: string;
  agent_name: string;
  page_url?: string;
  user_agent?: string;
  include_console_log?: boolean;
  console_log?: string;
};

export type TraceReportCreateResponse = {
  trace_id: string;
  directory: string;
  trace_json_path: string;
  markdown_path: string;
  beads_epic_id?: string;
  beads_task_id?: string;
  status: "saved_and_linked" | "saved_without_beads";
};

export type RecentTraceReport = {
  trace_id: string;
  title: string;
  created_at: string;
  thread_id?: string | null;
  agent_name?: string | null;
  directory: string;
  markdown_path: string;
};

export async function createTraceReport(
  payload: TraceReportCreateRequest,
): Promise<TraceReportCreateResponse> {
  const response = await fetch("/api/traces", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Failed to save trace with status ${response.status}`);
  }
  return (await response.json()) as TraceReportCreateResponse;
}

export async function fetchRecentTraceReports(limit = 5): Promise<RecentTraceReport[]> {
  const response = await fetch(`/api/traces/recent?limit=${limit}`, {
    method: "GET",
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Failed to load recent traces with status ${response.status}`);
  }
  const payload = (await response.json()) as { traces?: RecentTraceReport[] };
  return Array.isArray(payload.traces) ? payload.traces : [];
}
