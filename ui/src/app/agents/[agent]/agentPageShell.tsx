"use client";

import type { ReactElement, ReactNode } from "react";

import { AgentInspectorPanel } from "@/components/agents/AgentInspectorPanel";
import { AppNavBanner } from "@/components/navigation/AppNavBanner";
import { SearchBundlePanel } from "@/components/search/SearchBundlePanel";
import { ThreadDataPanel } from "@/components/thread/ThreadDataPanel";
import { SaveTraceButton } from "@/components/trace/SaveTraceButton";
import { SaveTraceDialog } from "@/components/trace/SaveTraceDialog";
import type { KnownFactItem } from "@/lib/api/threadDataClient";
import type { BundleProposal } from "@/lib/bundleProposalsStore";
import type { AgentItem, AgentMetadata } from "@/lib/agents";

type AgentRouteErrorProps = {
  currentAgent: string;
  onReturnHome?: () => void;
};

type AgentThreadHeaderProps = {
  currentAgent: string;
  description: string;
  threadId: string | null;
  threadIds: string[];
  warning: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDismissWarning: () => void;
  isTraceCaptureEnabled: boolean;
  onOpenTraceDialog: () => void;
};

type SharedAgentPageShellProps = {
  currentAgent: string;
  agents: AgentItem[];
  metadata: AgentMetadata | null;
  error: string;
  knownFacts: KnownFactItem[];
  knownFactsError: string | null;
  isLoadingKnownFacts: boolean;
  threadId: string | null;
  threadIds: string[];
  warning: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  onDismissWarning: () => void;
  isSearchAgent: boolean;
  isFloorPlanAgent: boolean;
  supportsImageAttachments: boolean;
  activeBundleId: string | null;
  bundleProposalError: string | null;
  bundleProposals: BundleProposal[];
  isLoadingBundleProposals: boolean;
  toolRenderers: ReactNode;
  previewPanel: ReactNode;
  attachmentPanel: ReactNode;
  chatPanel: ReactNode;
  isTraceCaptureEnabled: boolean;
  isTraceDialogOpen: boolean;
  onOpenTraceDialog: () => void;
  onCloseTraceDialog: () => void;
};

export function InvalidAgentPathView(): ReactElement {
  return (
    <main className="min-h-screen bg-white p-6">
      <p className="text-sm text-red-700">Invalid agent path.</p>
    </main>
  );
}

export function UnknownAgentView({
  currentAgent,
  onReturnHome,
}: AgentRouteErrorProps): ReactElement {
  return (
    <main className="min-h-screen bg-white p-6">
      <p className="text-sm text-red-700">
        Unknown agent `{currentAgent}`.
        <button className="ml-2 underline" onClick={onReturnHome} type="button">
          Return home
        </button>
      </p>
    </main>
  );
}

function AgentThreadHeader({
  currentAgent,
  description,
  threadId,
  threadIds,
  warning,
  onSelectThread,
  onCreateThread,
  onDismissWarning,
  isTraceCaptureEnabled,
  onOpenTraceDialog,
}: AgentThreadHeaderProps): ReactElement {
  const selectableThreadIds =
    threadId && !threadIds.includes(threadId) ? [threadId, ...threadIds] : threadIds;

  return (
    <header className="flex flex-col gap-1">
      <h2 className="text-lg font-semibold text-gray-900">{currentAgent}</h2>
      <p className="text-sm text-gray-600">{description}</p>
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-gray-600">
          Thread
          <select
            className="rounded border border-gray-300 bg-white px-2 py-1 text-sm text-gray-900"
            disabled={!threadId}
            onChange={(event) => {
              onSelectThread(event.target.value);
            }}
            value={threadId ?? ""}
          >
            {selectableThreadIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <button
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-800 hover:bg-gray-50"
          onClick={onCreateThread}
          type="button"
        >
          New thread
        </button>
        {isTraceCaptureEnabled && threadId ? (
          <SaveTraceButton
            onClick={() => {
              onOpenTraceDialog();
            }}
          />
        ) : null}
      </div>
      {warning ? (
        <div className="mt-1 flex items-start gap-2 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900">
          <span>{warning}</span>
          <button className="underline" onClick={onDismissWarning} type="button">
            Dismiss
          </button>
        </div>
      ) : null}
      {threadId ? <ThreadDataPanel key={threadId} threadId={threadId} /> : null}
    </header>
  );
}

export function SharedAgentPageShell({
  currentAgent,
  agents,
  metadata,
  error,
  knownFacts,
  knownFactsError,
  isLoadingKnownFacts,
  threadId,
  threadIds,
  warning,
  onSelectThread,
  onCreateThread,
  onDismissWarning,
  isSearchAgent,
  isFloorPlanAgent,
  supportsImageAttachments,
  activeBundleId,
  bundleProposalError,
  bundleProposals,
  isLoadingBundleProposals,
  toolRenderers,
  previewPanel,
  attachmentPanel,
  chatPanel,
  isTraceCaptureEnabled,
  isTraceDialogOpen,
  onOpenTraceDialog,
  onCloseTraceDialog,
}: SharedAgentPageShellProps): ReactElement {
  const selected = agents.find((item) => item.name === currentAgent) ?? null;
  const description = selected?.description ?? "Agent chat and tool-call stream.";
  const mainLayoutClassName = isSearchAgent
    ? "mx-auto grid max-w-[1900px] grid-cols-1 gap-4 p-6 xl:grid-cols-[minmax(300px,0.72fr)_minmax(0,1.28fr)_minmax(320px,360px)]"
    : "mx-auto grid max-w-[1700px] grid-cols-1 gap-4 p-6 lg:grid-cols-[minmax(320px,0.82fr)_minmax(0,1.18fr)]";
  const contentLayoutClassName = isFloorPlanAgent
    ? "grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,1.18fr)_minmax(360px,0.82fr)]"
    : "flex flex-1 flex-col gap-3";

  return (
    <main className="min-h-screen bg-white">
      <AppNavBanner currentAgentName={currentAgent} agents={agents} />
      <section className={mainLayoutClassName}>
        <AgentInspectorPanel
          error={error}
          isLoadingKnownFacts={isLoadingKnownFacts}
          knownFacts={knownFacts}
          knownFactsError={knownFactsError}
          metadata={metadata}
        />
        <section className="flex min-h-[70vh] min-w-0 flex-col gap-3 rounded border border-gray-200 bg-white p-3">
          <AgentThreadHeader
            currentAgent={currentAgent}
            description={description}
            threadId={threadId}
            threadIds={threadIds}
            warning={warning}
            onSelectThread={onSelectThread}
            onCreateThread={onCreateThread}
            onDismissWarning={onDismissWarning}
            isTraceCaptureEnabled={isTraceCaptureEnabled}
            onOpenTraceDialog={onOpenTraceDialog}
          />
          {isSearchAgent ? (
            <SearchBundlePanel
              activeBundleId={activeBundleId}
              error={bundleProposalError}
              isLoading={isLoadingBundleProposals}
              proposals={bundleProposals}
            />
          ) : (
            <div className={contentLayoutClassName}>
              <div className="flex min-h-0 min-w-0 flex-col gap-3">
                {toolRenderers}
                {previewPanel}
                {supportsImageAttachments ? attachmentPanel : null}
              </div>
              <div className="min-h-0 min-w-0">{chatPanel}</div>
            </div>
          )}
          {isTraceCaptureEnabled && threadId ? (
            <SaveTraceDialog
              agentName={currentAgent}
              onClose={onCloseTraceDialog}
              open={isTraceDialogOpen}
              threadId={threadId}
            />
          ) : null}
        </section>
        {isSearchAgent ? (
          <aside className="min-h-[70vh] min-w-0">
            <div className="flex min-h-[70vh] min-w-0 flex-col rounded border border-gray-200 bg-white p-2">
              {toolRenderers}
              {chatPanel}
            </div>
          </aside>
        ) : null}
      </section>
    </main>
  );
}
