"use client";

import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import {
  createTraceReport,
  fetchRecentTraceReports,
  type RecentTraceReport,
} from "@/lib/api/traceReportsClient";
import { getConsoleRecordsSnapshot } from "@/lib/feedbackCapture";

type SaveTraceDialogProps = {
  open: boolean;
  threadId: string;
  agentName: string;
  onClose: () => void;
};

function formatRecentTraceTitle(trace: RecentTraceReport): string {
  const createdAt = new Date(trace.created_at);
  return Number.isNaN(createdAt.valueOf())
    ? trace.title
    : `${trace.title} · ${createdAt.toLocaleString()}`;
}

function normalizeTraceError(error: Error): string {
  if (/Trace capture is unavailable/i.test(error.message)) {
    return `${error.message} The frontend trace button is enabled, but the backend trace route is missing.`;
  }
  return error.message;
}

export function SaveTraceDialog({
  open,
  threadId,
  agentName,
  onClose,
}: SaveTraceDialogProps): ReactElement | null {
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [recentTraces, setRecentTraces] = useState<RecentTraceReport[]>([]);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isLoadingRecent, setIsLoadingRecent] = useState<boolean>(false);

  useEffect(() => {
    if (!open) {
      setTitle("");
      setDescription("");
      setError(null);
      setSuccess(null);
      setRecentTraces([]);
      setIsSaving(false);
      setIsLoadingRecent(false);
      return;
    }

    let isCancelled = false;
    setIsLoadingRecent(true);
    void fetchRecentTraceReports(5)
      .then((traces) => {
        if (!isCancelled) {
          setRecentTraces(traces);
        }
      })
      .catch((loadError: unknown) => {
        if (!isCancelled) {
          const message = loadError instanceof Error ? normalizeTraceError(loadError) : "Failed to load recent traces.";
          setError(message);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoadingRecent(false);
        }
      });
    return () => {
      isCancelled = true;
    };
  }, [open]);

  if (!open) {
    return null;
  }

  async function handleSubmit(): Promise<void> {
    if (!title.trim()) {
      setError("Title is required.");
      return;
    }
    setIsSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await createTraceReport({
        title: title.trim(),
        ...(description.trim() ? { description: description.trim() } : {}),
        thread_id: threadId,
        agent_name: agentName,
        ...(typeof window !== "undefined" ? { page_url: window.location.href } : {}),
        ...(typeof navigator !== "undefined" ? { user_agent: navigator.userAgent } : {}),
        include_console_log: true,
        console_log: JSON.stringify(getConsoleRecordsSnapshot()),
      });
      setSuccess(
        response.status === "saved_and_linked"
          ? `Saved trace ${response.trace_id} and created ${response.beads_epic_id} / ${response.beads_task_id}. Saved at ${response.directory}.`
          : `Saved trace ${response.trace_id} at ${response.directory}, but Beads creation did not complete.`,
      );
      setRecentTraces(await fetchRecentTraceReports(5));
    } catch (submitError: unknown) {
      setError(
        submitError instanceof Error
          ? normalizeTraceError(submitError)
          : "Failed to save trace.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[2200] flex items-center justify-center bg-black/60 p-6">
      <div className="w-full max-w-md rounded bg-white p-4 shadow-2xl">
        <h2 className="text-lg font-semibold text-gray-900">Save current trace</h2>
        <p className="mt-1 text-sm text-gray-600">
          Save the current {agentName} thread trace and open Beads triage work.
        </p>
        <label className="mt-4 block text-sm text-gray-700" htmlFor="trace-title">
          Title
        </label>
        <input
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          id="trace-title"
          onChange={(event) => setTitle(event.target.value)}
          value={title}
        />
        <label className="mt-3 block text-sm text-gray-700" htmlFor="trace-description">
          Description (optional)
        </label>
        <textarea
          className="mt-1 min-h-28 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          id="trace-description"
          onChange={(event) => setDescription(event.target.value)}
          value={description}
        />
        {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
        {success ? <p className="mt-3 text-sm text-green-700">{success}</p> : null}
        <section className="mt-4 rounded border border-gray-200 bg-gray-50 p-3">
          <h3 className="text-sm font-semibold text-gray-900">Recent traces</h3>
          {isLoadingRecent ? <p className="mt-2 text-xs text-gray-500">Loading recent traces...</p> : null}
          {!isLoadingRecent && recentTraces.length === 0 ? (
            <p className="mt-2 text-xs text-gray-500">No saved traces yet.</p>
          ) : null}
          <ul className="mt-2 space-y-2 text-xs text-gray-700">
            {recentTraces.map((trace) => (
              <li key={trace.trace_id}>
                <p className="font-medium text-gray-900">{formatRecentTraceTitle(trace)}</p>
                <p className="text-gray-500">{trace.directory}</p>
              </li>
            ))}
          </ul>
        </section>
        <div className="mt-4 flex justify-end gap-2">
          <button
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-800 hover:bg-gray-50"
            onClick={onClose}
            type="button"
          >
            Close
          </button>
          <button
            className="rounded border border-gray-900 bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-60"
            disabled={isSaving}
            onClick={() => {
              void handleSubmit();
            }}
            type="button"
          >
            {isSaving ? "Saving..." : "Save trace"}
          </button>
        </div>
      </div>
    </div>
  );
}
