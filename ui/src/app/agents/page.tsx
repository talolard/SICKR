"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { fetchAgents, type AgentItem } from "@/lib/agents";

export default function AgentsPage(): React.ReactElement {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    void fetchAgents()
      .then((items) => {
        setAgents(items);
        setError("");
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agents.";
        setError(message);
      });
  }, []);

  return (
    <main className="min-h-screen bg-white">
      <AppNavBanner currentAgentName={null} agents={agents} />
      <section className="mx-auto max-w-[1700px] p-6">
        <h2 className="text-lg font-semibold text-gray-900">Agents</h2>
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {agents.map((agent) => (
            <Link
              key={agent.name}
              className="rounded border border-gray-200 p-4 hover:border-gray-400"
              href={`/agents/${agent.name}`}
            >
              <p className="text-sm font-semibold text-gray-900">{agent.name}</p>
              <p className="mt-1 text-sm text-gray-600">{agent.description}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
