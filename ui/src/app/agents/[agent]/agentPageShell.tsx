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
import { formatAgentName } from "@/lib/agentLabels";

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
  agentListError: string;
  isLoadingAgents: boolean;
  metadata: AgentMetadata | null;
  metadataError: string;
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
  const agentTitle = formatAgentName(currentAgent);

  return (
    <header className="flex flex-col gap-4 rounded-[24px] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.86))] p-4 shadow-[0_14px_40px_-36px_rgba(15,23,42,0.45)]">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-end xl:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
              Agent workspace
            </span>
            <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-900">
              {threadIds.length} thread{threadIds.length === 1 ? "" : "s"} tracked
            </span>
          </div>
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">{agentTitle}</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">{description}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex min-w-[220px] flex-col gap-1 text-xs font-medium uppercase tracking-[0.12em] text-slate-500">
            Thread
            <select
              className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 shadow-sm outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
              data-testid="agent-thread-select"
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
            className="rounded-2xl border border-slate-900 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            data-testid="new-thread-button"
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
      </div>
      {warning ? (
        <div className="flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50/90 p-3 text-xs text-amber-950">
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
  agentListError,
  isLoadingAgents,
  metadata,
  metadataError,
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
    ? "mx-auto flex w-full max-w-[1900px] flex-col gap-4 px-4 py-4 pb-6 xl:grid xl:h-[calc(100vh-5.5rem)] xl:grid-cols-[minmax(280px,0.68fr)_minmax(0,1.26fr)_minmax(340px,380px)]"
    : "mx-auto grid w-full max-w-[1720px] grid-cols-1 gap-4 px-4 py-4 pb-6 lg:grid-cols-[minmax(300px,0.78fr)_minmax(0,1.22fr)]";
  const contentLayoutClassName = isFloorPlanAgent
    ? "grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,1.18fr)_minmax(360px,0.82fr)]"
    : "flex flex-1 flex-col gap-3";

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(246,219,138,0.16),transparent_30%),radial-gradient(circle_at_top_right,rgba(31,74,123,0.12),transparent_32%),linear-gradient(180deg,#f6f3ee_0%,#f2eee8_46%,#ece7df_100%)]">
      <AppNavBanner
        currentAgentName={currentAgent}
        agents={agents}
        agentLoadError={agentListError}
        isLoadingAgents={isLoadingAgents}
      />
      <section className={mainLayoutClassName}>
        <AgentInspectorPanel
          metadataError={metadataError}
          isLoadingKnownFacts={isLoadingKnownFacts}
          knownFacts={knownFacts}
          knownFactsError={knownFactsError}
          metadata={metadata}
        />
        <section className="flex min-h-[70vh] min-w-0 flex-col gap-4 rounded-[28px] border border-slate-200/80 bg-white/95 p-4 shadow-[0_20px_55px_-40px_rgba(15,23,42,0.5)] backdrop-blur xl:min-h-0 xl:overflow-hidden">
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
            <div className="min-h-0 flex-1">
              <SearchBundlePanel
                activeBundleId={activeBundleId}
                error={bundleProposalError}
                isLoading={isLoadingBundleProposals}
                proposals={bundleProposals}
              />
            </div>
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
          <aside className="min-h-[70vh] min-w-0 xl:min-h-0" data-testid="search-chat-rail">
            <div className="flex h-full min-h-[70vh] min-w-0 flex-col rounded-[28px] border border-slate-200/80 bg-white/92 p-3 shadow-[0_18px_48px_-38px_rgba(15,23,42,0.5)] backdrop-blur xl:min-h-0 xl:overflow-hidden">
              <div className="mb-3 rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Conversation
                </p>
                <p className="mt-1 text-sm text-slate-600">
                  Keep follow-ups and long result explanations contained in the chat rail.
                </p>
              </div>
              <div className="min-h-0 flex-1">
                {toolRenderers}
                {chatPanel}
              </div>
            </div>
          </aside>
        ) : null}
      </section>
    </main>
  );
}
