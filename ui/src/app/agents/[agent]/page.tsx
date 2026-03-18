"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import type { ReactElement } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { useCopilotMessagesContext } from "@copilotkit/react-core";

import { useThreadSession } from "@/app/CopilotKitProviders";
import { AgentImageAttachmentPanel } from "@/components/attachments/AgentImageAttachmentPanel";
import { AgentChatSidebar } from "@/components/copilotkit/AgentChatSidebar";
import { CopilotToolRenderers } from "@/components/copilotkit/CopilotToolRenderers";
import type { AttachmentRef } from "@/lib/attachments";

import {
  InvalidAgentPathView,
  SharedAgentPageShell,
  UnknownAgentView,
} from "./agentPageShell";
import {
  isFloorPlanAgent,
  isSearchAgent,
  supportsImageAttachments,
  useAgentMetadataState,
  useCopilotAgentStateSync,
  useFloorPlanPreviewState,
  useKnownFactsState,
  useSearchBundleState,
  useThreadSnapshotSync,
} from "./agentPageHooks";

const LazyFloorPlanPreviewPanel = dynamic(
  () =>
    import("@/components/tooling/FloorPlanPreviewPanel").then(
      (module) => module.FloorPlanPreviewPanel,
    ),
  {
    ssr: false,
    loading: () => (
      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-lg font-semibold text-gray-900">Floor Plan Preview</h2>
        <p className="mt-2 text-sm text-gray-600">Loading preview panel...</p>
      </section>
    ),
  },
);

const traceCaptureEnabled = process.env.NEXT_PUBLIC_TRACE_CAPTURE_ENABLED === "1";

export default function AgentChatPage(): ReactElement {
  const params = useParams<{ agent: string }>();
  const router = useRouter();
  const currentAgent = params.agent;
  const { agentKey, agentName, threadId, threadIds, warning, selectThread, createThread, clearWarning } =
    useThreadSession();
  const { agent } = useAgent({ agentId: agentKey });
  const { messages, setMessages } = useCopilotMessagesContext();
  const [imageAttachments, setImageAttachments] = useState<AttachmentRef[]>([]);
  const [isTraceDialogOpen, setIsTraceDialogOpen] = useState<boolean>(false);
  const { agents, metadata, error } = useAgentMetadataState(currentAgent);
  const { knownFacts, knownFactsError, isLoadingKnownFacts } = useKnownFactsState(threadId);
  const {
    activeBundleId,
    bundleProposalError,
    bundleProposals,
    isLoadingBundleProposals,
    setActiveBundleId,
    addBundleProposal,
  } = useSearchBundleState(currentAgent, threadId);
  const { floorPlanPreview, saveRenderedFloorPlan } = useFloorPlanPreviewState(threadId);
  const searchAgent = isSearchAgent(currentAgent);
  const floorPlanAgent = isFloorPlanAgent(currentAgent);
  const imageAttachmentSupport = supportsImageAttachments(currentAgent);

  useCopilotAgentStateSync({
    agent,
    currentAgent,
    threadId,
    imageAttachments,
    bundleProposals,
  });
  useThreadSnapshotSync({
    agentKey,
    threadId,
    messages: messages as unknown[],
    replaceMessages: (nextMessages) => {
      setMessages(nextMessages as typeof messages);
    },
  });

  const toolRenderers = (
    <CopilotToolRenderers
      onBundleSelected={setActiveBundleId}
      threadId={threadId}
      onBundleProposed={addBundleProposal}
      onFloorPlanRendered={saveRenderedFloorPlan}
    />
  );

  if (agentName === null) {
    return <InvalidAgentPathView />;
  }

  if (!agents.some((item) => item.name === currentAgent) && agents.length > 0) {
    return (
      <UnknownAgentView
        currentAgent={currentAgent}
        onReturnHome={() => {
          router.push("/");
        }}
      />
    );
  }

  return (
    <SharedAgentPageShell
      currentAgent={currentAgent}
      agents={agents}
      metadata={metadata}
      error={error}
      knownFacts={knownFacts}
      knownFactsError={knownFactsError}
      isLoadingKnownFacts={isLoadingKnownFacts}
      threadId={threadId}
      threadIds={threadIds}
      warning={warning}
      onSelectThread={selectThread}
      onCreateThread={createThread}
      onDismissWarning={clearWarning}
      isSearchAgent={searchAgent}
      isFloorPlanAgent={floorPlanAgent}
      supportsImageAttachments={imageAttachmentSupport}
      activeBundleId={activeBundleId}
      bundleProposalError={bundleProposalError}
      bundleProposals={bundleProposals}
      isLoadingBundleProposals={isLoadingBundleProposals}
      toolRenderers={toolRenderers}
      previewPanel={
        !searchAgent ? <LazyFloorPlanPreviewPanel preview={floorPlanPreview} /> : null
      }
      attachmentPanel={
        <AgentImageAttachmentPanel
          onReadyAttachmentsChange={setImageAttachments}
          threadId={threadId}
          {...(floorPlanAgent
            ? {
                helperText:
                  "Uploaded images are added to floor-plan intake context for this thread.",
              }
            : {})}
        />
      }
      chatPanel={<AgentChatSidebar />}
      isTraceCaptureEnabled={traceCaptureEnabled}
      isTraceDialogOpen={isTraceDialogOpen}
      onOpenTraceDialog={() => {
        setIsTraceDialogOpen(true);
      }}
      onCloseTraceDialog={() => {
        setIsTraceDialogOpen(false);
      }}
    />
  );
}
