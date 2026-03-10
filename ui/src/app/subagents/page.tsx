"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SubagentBanner } from "@/components/subagents/SubagentBanner";
import { fetchSubagents, type SubagentItem } from "@/lib/subagents";

export default function SubagentsPage(): React.ReactElement {
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

  return (
    <main className="min-h-screen bg-white">
      <SubagentBanner currentSubagentName="" subagents={subagents} />
      <section className="mx-auto max-w-6xl px-4 py-6">
        <h2 className="mb-3 text-xl font-semibold text-gray-900">Available subagents</h2>
        {error.length > 0 ? <p className="text-red-700">{error}</p> : null}
        <ul className="grid gap-3">
          {subagents.map((subagent) => (
            <li key={subagent.name} className="rounded border border-gray-300 p-4">
              <div className="text-base font-semibold text-gray-900">{subagent.name}</div>
              <p className="mt-1 text-sm text-gray-700">{subagent.description}</p>
              <Link
                href={`/subagents/${subagent.name}`}
                className="mt-3 inline-block rounded bg-gray-900 px-3 py-2 text-sm text-white"
              >
                Open chat window
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
