"use client";

import { startTransition, useEffect, useMemo, useState } from "react";

import type { AttachmentRef } from "@/lib/attachments";
import {
  type KnownFactItem,
  listRoomThreadBundleProposals,
  listRoomThreadKnownFacts,
  listRoomThreadMessages,
  type ThreadMessageItem,
  ThreadDataRequestError,
} from "@/lib/api/threadDataClient";
import {
  appendBundleProposal,
  loadBundleProposals,
  mergeBundleProposals,
  replaceBundleProposals,
  type BundleProposal,
} from "@/lib/bundleProposalsStore";
import { startFeedbackCapture } from "@/lib/feedbackCapture";
import {
  type FloorPlanPreviewState,
  loadFloorPlanPreview,
  saveFloorPlanPreview,
} from "@/lib/floorPlanPreviewStore";
import {
  fetchAgentMetadata,
  fetchAgents,
  type AgentItem,
  type AgentMetadata,
} from "@/lib/agents";

export type AgentMetadataState = {
  agents: AgentItem[];
  metadata: AgentMetadata | null;
  agentListError: string;
  isLoadingAgents: boolean;
  metadataError: string;
};

export type KnownFactsState = {
  knownFacts: KnownFactItem[];
  knownFactsError: string | null;
  isLoadingKnownFacts: boolean;
};

export type SearchBundleState = {
  activeBundleId: string | null;
  bundleProposals: BundleProposal[];
  bundleProposalError: string | null;
  isLoadingBundleProposals: boolean;
  setActiveBundleId: (bundleId: string | null) => void;
  addBundleProposal: (proposal: BundleProposal) => void;
};

export type CopilotAgentStateBridge = {
  state: unknown;
  setState: (state: Record<string, unknown>) => void;
};

function stableJson(value: unknown): string {
  return JSON.stringify(value);
}

export function isSearchAgent(currentAgent: string): boolean {
  return currentAgent === "search";
}

export function isFloorPlanAgent(currentAgent: string): boolean {
  return currentAgent === "floor_plan_intake";
}

export function supportsImageAttachments(currentAgent: string): boolean {
  return currentAgent === "image_analysis" || currentAgent === "floor_plan_intake";
}

export function resolveAttachmentUri(uri: string): string {
  if (uri.startsWith("http://") || uri.startsWith("https://") || uri.startsWith("data:")) {
    return uri;
  }
  if (uri.startsWith("/attachments/")) {
    return uri;
  }
  return `/attachments/${uri.replace(/^\/+/, "")}`;
}

export function useAgentMetadataState(currentAgent: string): AgentMetadataState {
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [metadata, setMetadata] = useState<AgentMetadata | null>(null);
  const [agentListError, setAgentListError] = useState<string>("");
  const [isLoadingAgents, setIsLoadingAgents] = useState<boolean>(true);
  const [metadataError, setMetadataError] = useState<string>("");

  useEffect(() => {
    startFeedbackCapture();
  }, []);

  useEffect(() => {
    void fetchAgents()
      .then((items) => {
        setAgents(items);
        setAgentListError("");
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agents.";
        setAgentListError(message);
      })
      .finally(() => {
        setIsLoadingAgents(false);
      });
  }, []);

  useEffect(() => {
    void fetchAgentMetadata(currentAgent)
      .then((payload) => {
        setMetadata(payload);
        setMetadataError("");
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agent metadata.";
        setMetadataError(message);
      });
  }, [currentAgent]);

  return { agents, metadata, agentListError, isLoadingAgents, metadataError };
}

export function useKnownFactsState(
  roomId: string,
  threadId: string | null,
): KnownFactsState {
  const [knownFacts, setKnownFacts] = useState<KnownFactItem[]>([]);
  const [knownFactsError, setKnownFactsError] = useState<string | null>(null);
  const [isLoadingKnownFacts, setIsLoadingKnownFacts] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    if (!threadId) {
      startTransition(() => {
        setKnownFacts([]);
        setKnownFactsError(null);
        setIsLoadingKnownFacts(false);
      });
      return () => {
        active = false;
      };
    }

    startTransition(() => {
      setKnownFacts([]);
      setKnownFactsError(null);
      setIsLoadingKnownFacts(true);
    });
    void listRoomThreadKnownFacts(roomId, threadId)
      .then((persistedKnownFacts) => {
        if (!active) {
          return;
        }
        setKnownFacts(persistedKnownFacts);
      })
      .catch((fetchError: unknown) => {
        if (!active) {
          return;
        }
        if (fetchError instanceof ThreadDataRequestError && fetchError.status === 404) {
          return;
        }
        setKnownFactsError(
          fetchError instanceof Error ? fetchError.message : "Failed to load known facts.",
        );
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsLoadingKnownFacts(false);
      });

    return () => {
      active = false;
    };
  }, [roomId, threadId]);

  return { knownFacts, knownFactsError, isLoadingKnownFacts };
}

export function useSearchBundleState(
  currentAgent: string,
  roomId: string,
  threadId: string | null,
): SearchBundleState {
  const [bundleProposals, setBundleProposals] = useState<BundleProposal[]>([]);
  const [bundleProposalError, setBundleProposalError] = useState<string | null>(null);
  const [activeBundleId, setActiveBundleId] = useState<string | null>(null);
  const [isLoadingBundleProposals, setIsLoadingBundleProposals] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    if (!threadId || !isSearchAgent(currentAgent)) {
      startTransition(() => {
        setActiveBundleId(null);
        setBundleProposals([]);
        setBundleProposalError(null);
        setIsLoadingBundleProposals(false);
      });
      return () => {
        active = false;
      };
    }

    const localProposals = loadBundleProposals(threadId);
    startTransition(() => {
      setActiveBundleId(null);
      setBundleProposals(localProposals);
      setBundleProposalError(null);
      setIsLoadingBundleProposals(true);
    });
    void listRoomThreadBundleProposals(roomId, threadId)
      .then((persistedProposals) => {
        if (!active) {
          return;
        }
        setBundleProposals(
          replaceBundleProposals(threadId, mergeBundleProposals(persistedProposals, localProposals)),
        );
      })
      .catch((fetchError: unknown) => {
        if (!active) {
          return;
        }
        if (fetchError instanceof ThreadDataRequestError && fetchError.status === 404) {
          return;
        }
        setBundleProposalError(
          fetchError instanceof Error
            ? fetchError.message
            : "Failed to load saved bundle proposals.",
        );
      })
      .finally(() => {
        if (!active) {
          return;
        }
        setIsLoadingBundleProposals(false);
      });

    return () => {
      active = false;
    };
  }, [currentAgent, roomId, threadId]);

  const addBundleProposal = (proposal: BundleProposal): void => {
    setActiveBundleId(proposal.bundle_id);
    if (!threadId) {
      setBundleProposals((current) => mergeBundleProposals([proposal], current));
      return;
    }
    setBundleProposalError(null);
    setBundleProposals(appendBundleProposal(threadId, proposal));
  };

  return {
    activeBundleId,
    bundleProposalError,
    bundleProposals,
    isLoadingBundleProposals,
    setActiveBundleId,
    addBundleProposal,
  };
}

export function useCopilotAgentStateSync(params: {
  agent: CopilotAgentStateBridge;
  currentAgent: string;
  roomId: string;
  sessionId: string;
  threadId: string | null;
  imageAttachments: AttachmentRef[];
  bundleProposals: BundleProposal[];
}): void {
  const { agent, currentAgent, roomId, sessionId, threadId, imageAttachments, bundleProposals } =
    params;

  useEffect(() => {
    if (!threadId) {
      return;
    }
    const attachmentsForAgent = supportsImageAttachments(currentAgent) ? imageAttachments : [];
    const bundleProposalsForAgent = isSearchAgent(currentAgent) ? bundleProposals : [];
    const previousState =
      typeof agent.state === "object" && agent.state !== null
        ? (agent.state as Record<string, unknown>)
        : {};
    if (
      previousState.session_id === sessionId &&
      previousState.room_id === roomId &&
      previousState.thread_id === threadId &&
      stableJson(previousState.attachments ?? []) === stableJson(attachmentsForAgent) &&
      stableJson(previousState.bundle_proposals ?? []) === stableJson(bundleProposalsForAgent)
    ) {
      return;
    }
    agent.setState({
      ...previousState,
      session_id: sessionId,
      room_id: roomId,
      thread_id: threadId,
      attachments: attachmentsForAgent,
      bundle_proposals: bundleProposalsForAgent,
    });
  }, [agent, bundleProposals, currentAgent, imageAttachments, roomId, sessionId, threadId]);
}

export function useThreadMessagesHydration(params: {
  roomId: string;
  threadId: string | null;
  replaceMessages: (messages: unknown[]) => void;
}): void {
  const { roomId, threadId, replaceMessages } = params;

  useEffect(() => {
    if (!threadId) {
      replaceMessages([]);
      return;
    }
    let active = true;
    replaceMessages([]);
    void listRoomThreadMessages(roomId, threadId)
      .then((persistedMessages: ThreadMessageItem[]) => {
        if (!active) {
          return;
        }
        replaceMessages(persistedMessages);
      })
      .catch((fetchError: unknown) => {
        if (!active) {
          return;
        }
        if (fetchError instanceof ThreadDataRequestError && fetchError.status === 404) {
          replaceMessages([]);
          return;
        }
        replaceMessages([]);
      });
    return () => {
      active = false;
    };
  }, [replaceMessages, roomId, threadId]);
}

export function useFloorPlanPreviewState(threadId: string | null): {
  floorPlanPreview: FloorPlanPreviewState | null;
  saveRenderedFloorPlan: (snapshot: Omit<FloorPlanPreviewState, "threadId">) => void;
} {
  const [activeFloorPlanPreview, setActiveFloorPlanPreview] = useState<FloorPlanPreviewState | null>(
    null,
  );

  const persistedFloorPlanPreview = useMemo((): FloorPlanPreviewState | null => {
    if (!threadId) {
      return null;
    }
    return loadFloorPlanPreview(threadId);
  }, [threadId]);

  const floorPlanPreview = useMemo((): FloorPlanPreviewState | null => {
    if (!threadId) {
      return null;
    }
    if (activeFloorPlanPreview?.threadId === threadId) {
      return activeFloorPlanPreview;
    }
    return persistedFloorPlanPreview;
  }, [activeFloorPlanPreview, persistedFloorPlanPreview, threadId]);

  const saveRenderedFloorPlan = (snapshot: Omit<FloorPlanPreviewState, "threadId">): void => {
    const resolvedImages = snapshot.images.map((image) => ({
      ...image,
      uri: resolveAttachmentUri(image.uri),
    }));
    const nextSnapshot: FloorPlanPreviewState = {
      ...snapshot,
      threadId: threadId ?? "pending",
      images: resolvedImages,
    };
    setActiveFloorPlanPreview(nextSnapshot);
    if (threadId) {
      saveFloorPlanPreview(nextSnapshot);
    }
  };

  return { floorPlanPreview, saveRenderedFloorPlan };
}
