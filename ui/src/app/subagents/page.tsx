"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { fetchSubagents, type SubagentItem } from "@/lib/subagents";

export default function SubagentsPage(): React.ReactElement {
  const router = useRouter();
  const [subagents, setSubagents] = useState<SubagentItem[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    void fetchSubagents()
      .then((items) => {
        setSubagents(items);
        const first = items[0];
        if (first) {
          router.replace(`/subagents/${first.name}`);
        }
      })
      .catch((fetchError: unknown) => {
        const message =
          fetchError instanceof Error ? fetchError.message : "Failed to load subagents.";
        setError(message);
      });
  }, [router]);

  return (
    <main className="min-h-screen bg-white">
      <AppNavBanner currentSubagentName={null} subagents={subagents} />
      <section className="mx-auto max-w-[1700px] p-6">
        {error ? <p className="text-sm text-red-700">{error}</p> : <p className="text-sm text-gray-700">Loading subagents...</p>}
      </section>
    </main>
  );
}
