"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ReactElement } from "react";
import { CopilotSidebar, useAgent } from "@copilotkit/react-core/v2";

import { useThreadSession } from "@/app/CopilotKitProviders";
import { AgentInspectorPanel } from "@/components/agents/AgentInspectorPanel";
import { AgentImageAttachmentPanel } from "@/components/attachments/AgentImageAttachmentPanel";
import { CopilotToolRenderers } from "@/components/copilotkit/CopilotToolRenderers";
import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { SearchBundlePanel } from "@/components/search/SearchBundlePanel";
import { ThreadDataPanel } from "@/components/thread/ThreadDataPanel";
import { SaveTraceButton } from "@/components/trace/SaveTraceButton";
import { SaveTraceDialog } from "@/components/trace/SaveTraceDialog";
import { FloorPlanPreviewPanel } from "@/components/tooling/FloorPlanPreviewPanel";
import type { AttachmentRef } from "@/lib/attachments";
import {
  listThreadBundleProposals,
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

const traceCaptureEnabled = process.env.NEXT_PUBLIC_TRACE_CAPTURE_ENABLED === "1";

function resolveAttachmentUri(uri: string): string {
  if (uri.startsWith("http://") || uri.startsWith("https://") || uri.startsWith("data:")) {
    return uri;
  }
  if (uri.startsWith("/attachments/")) {
    return uri;
  }
  return `/attachments/${uri.replace(/^\/+/, "")}`;
}

export default function AgentChatPage(): ReactElement {
  const params = useParams<{ agent: string }>();
  const router = useRouter();
  const currentAgent = params.agent;
  const { agentKey, agentName, threadId, threadIds, warning, selectThread, createThread, clearWarning } =
    useThreadSession();
  const { agent } = useAgent({ agentId: agentKey });
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [metadata, setMetadata] = useState<AgentMetadata | null>(null);
  const [error, setError] = useState<string>("");
  const [floorPlanPreview, setFloorPlanPreview] = useState<FloorPlanPreviewState | null>(null);
  const [imageAttachments, setImageAttachments] = useState<AttachmentRef[]>([]);
  const [bundleProposals, setBundleProposals] = useState<BundleProposal[]>([]);
  const [bundleProposalError, setBundleProposalError] = useState<string | null>(null);
  const [isLoadingBundleProposals, setIsLoadingBundleProposals] = useState<boolean>(false);
  const [isTraceDialogOpen, setIsTraceDialogOpen] = useState<boolean>(false);

  useEffect(() => {
    startFeedbackCapture();
  }, []);

  useEffect(() => {
    void fetchAgents()
      .then((items) => setAgents(items))
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agents.";
        setError(message);
      });
  }, []);

  useEffect(() => {
    void fetchAgentMetadata(currentAgent)
      .then((payload) => {
        setMetadata(payload);
        setError("");
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : "Failed to load agent metadata.";
        setError(message);
      });
  }, [currentAgent]);

  useEffect(() => {
    let active = true;
    if (!threadId) {
      setFloorPlanPreview(null);
      setBundleProposals([]);
      setBundleProposalError(null);
      setIsLoadingBundleProposals(false);
      return () => {
        active = false;
      };
    }

    setFloorPlanPreview(loadFloorPlanPreview(threadId));
    if (currentAgent !== "search") {
      setBundleProposals([]);
      setBundleProposalError(null);
      setIsLoadingBundleProposals(false);
      return () => {
        active = false;
      };
    }

    const localProposals = loadBundleProposals(threadId);
    setBundleProposals(localProposals);
    setBundleProposalError(null);
    setIsLoadingBundleProposals(true);
    void listThreadBundleProposals(threadId)
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
  }, [currentAgent, threadId]);

  useEffect(() => {
    if (!threadId) {
      return;
    }
    const attachmentsForAgent = currentAgent === "image_analysis" ? imageAttachments : [];
    const previousState =
      typeof agent.state === "object" && agent.state !== null
        ? (agent.state as Record<string, unknown>)
        : {};
    agent.setState({
      ...previousState,
      session_id: threadId,
      thread_id: threadId,
      attachments: attachmentsForAgent,
      bundle_proposals: currentAgent === "search" ? bundleProposals : [],
    });
  }, [agent, bundleProposals, currentAgent, imageAttachments, threadId]);

  const selected = useMemo(() => {
    return agents.find((item) => item.name === currentAgent) ?? null;
  }, [currentAgent, agents]);

  if (agentName === null) {
    return (
      <main className="min-h-screen bg-white p-6">
        <p className="text-sm text-red-700">Invalid agent path.</p>
      </main>
    );
  }

  if (selected === null && agents.length > 0) {
    return (
      <main className="min-h-screen bg-white p-6">
        <p className="text-sm text-red-700">
          Unknown agent `{currentAgent}`.
          <button className="ml-2 underline" onClick={() => router.push("/")} type="button">
            Return home
          </button>
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white">
      <AppNavBanner currentAgentName={currentAgent} agents={agents} />
      <section className="mx-auto grid max-w-[1700px] grid-cols-1 gap-4 p-6 lg:grid-cols-[0.85fr_1.15fr]">
        <AgentInspectorPanel error={error} metadata={metadata} />
        <section className="flex min-h-[70vh] flex-col gap-3 rounded border border-gray-200 bg-white p-3">
          <header className="flex flex-col gap-1">
            <h2 className="text-lg font-semibold text-gray-900">{currentAgent}</h2>
            <p className="text-sm text-gray-600">{selected?.description ?? "Agent chat and tool-call stream."}</p>
            <div className="mt-2 flex flex-wrap items-end gap-2">
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
                  {(threadId && !threadIds.includes(threadId) ? [threadId, ...threadIds] : threadIds).map((id) => (
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
              {traceCaptureEnabled && threadId ? (
                <SaveTraceButton
                  onClick={() => {
                    setIsTraceDialogOpen(true);
                  }}
                />
              ) : null}
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
            <FloorPlanPreviewPanel preview={floorPlanPreview} />
            {currentAgent === "image_analysis" ? (
              <AgentImageAttachmentPanel
                onReadyAttachmentsChange={setImageAttachments}
                threadId={threadId}
              />
            ) : null}
          </header>
          <div
            className={
              currentAgent === "search"
                ? "grid flex-1 gap-3 xl:grid-cols-[minmax(0,1fr)_360px]"
                : "flex flex-1 flex-col gap-3"
            }
          >
            <section className="flex min-h-0 flex-col gap-3">
              <CopilotToolRenderers
                threadId={threadId}
                onBundleProposed={(proposal) => {
                  if (!threadId) {
                    setBundleProposals((current) => mergeBundleProposals([proposal], current));
                    return;
                  }
                  setBundleProposalError(null);
                  setBundleProposals(appendBundleProposal(threadId, proposal));
                }}
                onFloorPlanRendered={(snapshot) => {
                  const resolvedImages = snapshot.images.map((image) => ({
                    ...image,
                    uri: resolveAttachmentUri(image.uri),
                  }));
                  const nextSnapshot: FloorPlanPreviewState = {
                    ...snapshot,
                    threadId: threadId ?? "pending",
                    images: resolvedImages,
                  };
                  setFloorPlanPreview(nextSnapshot);
                  if (threadId) {
                    saveFloorPlanPreview(nextSnapshot);
                  }
                }}
              />
              <CopilotSidebar />
            </section>
            {currentAgent === "search" ? (
              <SearchBundlePanel
                error={bundleProposalError}
                isLoading={isLoadingBundleProposals}
                proposals={bundleProposals}
              />
            ) : null}
          </div>
          {traceCaptureEnabled && threadId ? (
            <SaveTraceDialog
              agentName={currentAgent}
              onClose={() => {
                setIsTraceDialogOpen(false);
              }}
              open={isTraceDialogOpen}
              threadId={threadId}
            />
          ) : null}
        </section>
      </section>
    </main>
  );
}
