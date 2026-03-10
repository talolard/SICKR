"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { CopilotSidebar, useAgent } from "@copilotkit/react-core/v2";

import { useThreadSession } from "@/app/CopilotKitProviders";
import { CopilotToolRenderers } from "@/components/copilotkit/CopilotToolRenderers";
import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { SubagentInspectorPanel } from "@/components/subagents/SubagentInspectorPanel";
import { ThreadDataPanel } from "@/components/thread/ThreadDataPanel";
import {
  fetchSubagentMetadata,
  fetchSubagents,
  type SubagentItem,
  type SubagentMetadata,
} from "@/lib/subagents";

export default function SubagentChatPage(): React.ReactElement {
  const params = useParams<{ agent: string }>();
  const router = useRouter();
  const currentAgent = params.agent;
  const { agentKey, subagentName, threadId, threadIds, warning, selectThread, createThread, clearWarning } =
    useThreadSession();
  const { agent } = useAgent({ agentId: agentKey });
  const [subagents, setSubagents] = useState<SubagentItem[]>([]);
  const [metadata, setMetadata] = useState<SubagentMetadata | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    void fetchSubagents()
      .then((items) => setSubagents(items))
      .catch((fetchError: unknown) => {
        const message =
          fetchError instanceof Error ? fetchError.message : "Failed to load subagents.";
        setError(message);
      });
  }, []);

  useEffect(() => {
    void fetchSubagentMetadata(currentAgent)
      .then((payload) => {
        setMetadata(payload);
        setError("");
      })
      .catch((fetchError: unknown) => {
        const message =
          fetchError instanceof Error ? fetchError.message : "Failed to load subagent metadata.";
        setError(message);
      });
  }, [currentAgent]);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    const previousState =
      typeof agent.state === "object" && agent.state !== null
        ? (agent.state as Record<string, unknown>)
        : {};
    agent.setState({
      ...previousState,
      session_id: threadId,
      thread_id: threadId,
    });
  }, [agent, threadId]);

  const selected = useMemo(() => {
    return subagents.find((subagent) => subagent.name === currentAgent) ?? null;
  }, [currentAgent, subagents]);

  if (subagentName === null) {
    return (
      <main className="min-h-screen bg-white p-6">
        <p className="text-sm text-red-700">Invalid subagent path.</p>
      </main>
    );
  }

  if (selected === null && subagents.length > 0) {
    return (
      <main className="min-h-screen bg-white p-6">
        <p className="text-sm text-red-700">
          Unknown subagent `{currentAgent}`.
          <button className="ml-2 underline" onClick={() => router.push("/")} type="button">
            Return home
          </button>
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white">
      <AppNavBanner currentSubagentName={currentAgent} subagents={subagents} />
      <section className="mx-auto grid max-w-[1700px] grid-cols-1 gap-4 p-6 lg:grid-cols-[0.85fr_1.15fr]">
        <SubagentInspectorPanel error={error} metadata={metadata} />
        <section className="flex min-h-[70vh] flex-col gap-3 rounded border border-gray-200 bg-white p-3">
          <header className="flex flex-col gap-1">
            <h2 className="text-lg font-semibold text-gray-900">{currentAgent}</h2>
            <p className="text-sm text-gray-600">
              {selected?.description ?? "Subagent chat and tool-call stream."}
            </p>
            <div className="mt-2 flex items-end gap-2">
              <label className="flex flex-col gap-1 text-xs text-gray-600">
                Thread
                <select
                  className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900"
                  disabled={!threadId}
                  onChange={(event) => {
                    selectThread(event.target.value);
                  }}
                  value={threadId ?? ""}
                >
                  {(threadId && !threadIds.includes(threadId)
                    ? [threadId, ...threadIds]
                    : threadIds
                  ).map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                </select>
              </label>
              <button
                className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-800 hover:bg-gray-50"
                onClick={createThread}
                type="button"
              >
                New thread
              </button>
            </div>
            {warning ? (
              <div className="mt-1 flex items-start gap-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
                <span>{warning}</span>
                <button className="underline" onClick={clearWarning} type="button">
                  Dismiss
                </button>
              </div>
            ) : null}
            {threadId ? <ThreadDataPanel threadId={threadId} /> : null}
          </header>
          <CopilotToolRenderers />
          <CopilotSidebar />
        </section>
      </section>
    </main>
  );
}
