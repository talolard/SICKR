"use client";

import { useEffect, useState } from "react";

import { StudioShowcaseLayout } from "@/components/agents/StudioShowcaseLayout";
import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { fetchAgents, type AgentItem } from "@/lib/agents";

export default function Home(): React.ReactElement {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [error, setError] = useState<string>("");
  const [isLoadingAgents, setIsLoadingAgents] = useState<boolean>(true);

  useEffect(() => {
    void fetchAgents()
      .then((items) => {
        setAgents(items);
        setError("");
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agents.";
        setError(message);
      })
      .finally(() => {
        setIsLoadingAgents(false);
      });
  }, []);

  return (
    <main className="editorial-page">
      <AppNavBanner
        currentAgentName={null}
        agents={agents}
        agentLoadError={error}
        isLoadingAgents={isLoadingAgents}
      />
      <StudioShowcaseLayout
        agents={agents}
        description="Beautiful, accurate interior design made accessible, from first measurements to shoppable rooms and styling guidance."
        error={error}
        eyebrow="Designer's Studio"
        isLoadingAgents={isLoadingAgents}
        title="Welcome to your Designer's Studio"
      />
    </main>
  );
}
