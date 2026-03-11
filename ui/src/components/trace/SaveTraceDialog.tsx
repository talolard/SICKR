"use client";

import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import { createTraceReport } from "@/lib/api/traceReportsClient";
import { getConsoleRecordsSnapshot } from "@/lib/feedbackCapture";

type SaveTraceDialogProps = {
  open: boolean;
  threadId: string;
  agentName: string;
  onClose: () => void;
};

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
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    if (!open) {
      setTitle("");
      setDescription("");
      setError(null);
      setSuccess(null);
      setIsSaving(false);
    }
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
          ? `Saved trace ${response.trace_id} and created ${response.beads_epic_id} / ${response.beads_task_id}.`
          : `Saved trace ${response.trace_id}, but Beads creation did not complete.`,
      );
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save trace.");
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
