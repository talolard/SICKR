import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { SaveTraceDialog } from "./SaveTraceDialog";

const mocks = vi.hoisted(() => ({
  createTraceReport: vi.fn(),
  fetchRecentTraceReports: vi.fn(),
}));

vi.mock("@/lib/api/traceReportsClient", () => ({
  createTraceReport: mocks.createTraceReport,
  fetchRecentTraceReports: mocks.fetchRecentTraceReports,
}));

vi.mock("@/lib/feedbackCapture", () => ({
  getConsoleRecordsSnapshot: () => [{ level: "info", args: ["hello"], timestamp: "2026-03-11T10:00:00Z" }],
}));

describe("SaveTraceDialog", () => {
  it("requires a title before saving", async () => {
    mocks.fetchRecentTraceReports.mockResolvedValueOnce([]);

    render(
      <SaveTraceDialog
        open
        threadId="thread-1"
        agentName="search"
        onClose={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Save trace" }));

    expect(await screen.findByText("Title is required.")).toBeInTheDocument();
  });

  it("loads and renders recent traces", async () => {
    mocks.fetchRecentTraceReports.mockResolvedValueOnce([
      {
        trace_id: "trace-1",
        title: "Recent trace",
        created_at: "2026-03-11T10:00:00Z",
        directory: "/tmp/traces/trace-1",
        markdown_path: "/tmp/traces/trace-1/report.md",
      },
    ]);

    render(
      <SaveTraceDialog
        open
        threadId="thread-1"
        agentName="search"
        onClose={() => {}}
      />,
    );

    expect(await screen.findByText(/Recent trace/)).toBeInTheDocument();
    expect(screen.getByText("/tmp/traces/trace-1")).toBeInTheDocument();
  });

  it("renders a clearer mismatch diagnostic when trace capture backend is unavailable", async () => {
    mocks.fetchRecentTraceReports.mockRejectedValueOnce(
      new Error("Trace capture is unavailable. Enable TRACE_CAPTURE_ENABLED on the backend or hide the UI flag."),
    );

    render(
      <SaveTraceDialog
        open
        threadId="thread-1"
        agentName="search"
        onClose={() => {}}
      />,
    );

    expect(
      await screen.findByText(/frontend trace button is enabled, but the backend trace route is missing/i),
    ).toBeInTheDocument();
  });

  it("submits the trace payload and renders success with the saved path", async () => {
    mocks.fetchRecentTraceReports
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          trace_id: "trace-123",
          title: "Investigate latency",
          created_at: "2026-03-11T10:00:00Z",
          directory: "/tmp/traces/trace-123",
          markdown_path: "/tmp/traces/trace-123/report.md",
        },
      ]);
    mocks.createTraceReport.mockResolvedValueOnce({
      trace_id: "trace-123",
      directory: "/tmp/traces/trace-123",
      trace_json_path: "/tmp/traces/trace-123/trace.json",
      markdown_path: "/tmp/traces/trace-123/report.md",
      beads_epic_id: "epic-1",
      beads_task_id: "epic-1.1",
      status: "saved_and_linked",
    });

    render(
      <SaveTraceDialog
        open
        threadId="thread-1"
        agentName="search"
        onClose={() => {}}
      />,
    );

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Investigate latency" } });
    fireEvent.change(screen.getByLabelText("Description (optional)"), {
      target: { value: "Search took too long." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save trace" }));

    await waitFor(() => {
      expect(mocks.createTraceReport).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Investigate latency",
          description: "Search took too long.",
          thread_id: "thread-1",
          agent_name: "search",
          include_console_log: true,
        }),
      );
    });
    expect(
      await screen.findByText(/Saved trace trace-123 and created epic-1/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/Saved at \/tmp\/traces\/trace-123/)).toBeInTheDocument();
  });
});
