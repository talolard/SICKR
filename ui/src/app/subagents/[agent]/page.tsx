"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { SubagentBanner } from "@/components/subagents/SubagentBanner";
import { fetchSubagents, type SubagentItem } from "@/lib/subagents";

export default function SubagentChatPage(): React.ReactElement {
  const params = useParams<{ agent: string }>();
  const currentAgent = params.agent;
  const [subagents, setSubagents] = useState<SubagentItem[]>([]);
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

  const selected = useMemo(() => {
    return subagents.find((subagent) => subagent.name === currentAgent) ?? null;
  }, [currentAgent, subagents]);

  const chatUrl = selected?.chat_proxy_path ?? `/api/subagents/${currentAgent}/chat/`;

  return (
    <main className="min-h-screen bg-white">
      <SubagentBanner currentSubagentName={currentAgent} subagents={subagents} />
      <section className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {selected?.description ?? "Subagent chat routed through PydanticAI web UI."}
          </p>
          <Link href={chatUrl} className="text-sm text-blue-700 underline" target="_blank">
            Open in new tab
          </Link>
        </div>
        {error.length > 0 ? <p className="text-red-700">{error}</p> : null}
        <iframe
          src={chatUrl}
          title={`subagent-${currentAgent}-chat`}
          className="h-[calc(100vh-12rem)] w-full rounded border border-gray-300"
        />
      </section>
    </main>
  );
}
