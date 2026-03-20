"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import type { ReactElement } from "react";
import { useAgent } from "@copilotkit/react-core/v2";
import { useCopilotMessagesContext } from "@copilotkit/react-core";

import { useThreadSession } from "@/app/CopilotKitProviders";
import { AgentImageAttachmentPanel } from "@/components/attachments/AgentImageAttachmentPanel";
import { AgentChatSidebar } from "@/components/copilotkit/AgentChatSidebar";
import { CopilotToolRenderers } from "@/components/copilotkit/CopilotToolRenderers";
import { ImageAnalysisWorkspacePanel } from "@/components/tooling/ImageAnalysisWorkspacePanel";
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
      <section className="editorial-panel-elevated rounded-[30px] p-4">
        <p className="editorial-eyebrow">Floor plan preview</p>
        <h2 className="editorial-display mt-3 text-[1.8rem] leading-none text-primary">
          Drafting surface
        </h2>
        <p className="mt-3 text-sm leading-6 text-on-surface-variant">
          Loading preview panel...
        </p>
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
  const { agents, metadata, agentListError, isLoadingAgents, metadataError } =
    useAgentMetadataState(currentAgent);
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
  const replaceThreadMessages = useCallback((nextMessages: unknown[]) => {
    setMessages(nextMessages as typeof messages);
  }, [setMessages]);

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
    replaceMessages: replaceThreadMessages,
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
      agentListError={agentListError}
      isLoadingAgents={isLoadingAgents}
      metadata={metadata}
      metadataError={metadataError}
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
      supportsImageAttachments={imageAttachmentSupport}
      activeBundleId={activeBundleId}
      bundleProposalError={bundleProposalError}
      bundleProposals={bundleProposals}
      isLoadingBundleProposals={isLoadingBundleProposals}
      toolRenderers={toolRenderers}
      previewPanel={
        !searchAgent ? (
          floorPlanAgent ? (
            <LazyFloorPlanPreviewPanel preview={floorPlanPreview} />
          ) : (
            <ImageAnalysisWorkspacePanel attachments={imageAttachments} />
          )
        ) : null
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
      chatPanel={<AgentChatSidebar currentAgent={currentAgent} />}
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
