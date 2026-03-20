"use client";

import type { ReactElement, ReactNode } from "react";

import { AgentInspectorPanel } from "@/components/agents/AgentInspectorPanel";
import { resolveWorkspacePresentation } from "@/components/agents/workspacePresentation";
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
  const presentation = resolveWorkspacePresentation(currentAgent);
  const hasTrackedThread = Boolean(threadId);

  return (
    <header className="rounded-[30px] bg-[color:var(--surface-container-low)] px-5 py-4 shadow-[var(--panel-shadow)]">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-[color:var(--surface-container-lowest)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
              {presentation.capabilityLabel}
            </span>
            <span className="rounded-full bg-[color:var(--tertiary-fixed)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
              {threadIds.length} thread{threadIds.length === 1 ? "" : "s"} tracked
            </span>
          </div>
          <div>
            <h1 className="editorial-display text-[2rem] leading-none text-primary md:text-[2.35rem]">
              {presentation.title}
            </h1>
            {!hasTrackedThread ? (
              <p className="mt-2 max-w-3xl text-sm leading-6 text-on-surface-variant">
                {presentation.description}
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex min-w-[240px] flex-col gap-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
              Tracked thread
            </span>
            <select
              className="rounded-full bg-[color:var(--surface-container-lowest)] px-4 py-2.5 text-sm font-semibold text-primary shadow-[var(--panel-shadow)] outline-none"
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
            className="rounded-full bg-[color:var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_20px_35px_rgba(24,36,27,0.18)]"
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
        <div className="mt-3 flex items-start gap-2 rounded-[22px] bg-amber-50 px-4 py-3 text-xs text-amber-950">
          <span>{warning}</span>
          <button className="underline" onClick={onDismissWarning} type="button">
            Dismiss
          </button>
        </div>
      ) : null}
      {threadId ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
            Thread data
          </summary>
          <div className="mt-3">
            <ThreadDataPanel key={threadId} threadId={threadId} />
          </div>
        </details>
      ) : null}
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
  const presentation = resolveWorkspacePresentation(currentAgent, selected?.description);

  return (
    <main className="editorial-page min-h-screen">
      <AppNavBanner
        currentAgentName={currentAgent}
        agents={agents}
        agentLoadError={agentListError}
        isLoadingAgents={isLoadingAgents}
      />
      <section className="mx-auto grid w-full max-w-[1860px] grid-cols-1 gap-5 px-4 py-5 pb-6 xl:h-[calc(100vh-5.5rem)] xl:grid-cols-[260px_minmax(0,1fr)_360px] xl:px-6">
        <AgentInspectorPanel
          currentAgent={currentAgent}
          metadataError={metadataError}
          isLoadingKnownFacts={isLoadingKnownFacts}
          knownFacts={knownFacts}
          knownFactsError={knownFactsError}
          metadata={metadata}
        />
        <section className="flex min-h-[70vh] min-w-0 flex-col gap-4 rounded-[34px] bg-[rgba(255,248,242,0.78)] p-4 shadow-[var(--panel-shadow-strong)] backdrop-blur xl:min-h-0 xl:overflow-hidden">
          {toolRenderers}
          <AgentThreadHeader
            currentAgent={currentAgent}
            threadId={threadId}
            threadIds={threadIds}
            warning={warning}
            onSelectThread={onSelectThread}
            onCreateThread={onCreateThread}
            onDismissWarning={onDismissWarning}
            isTraceCaptureEnabled={isTraceCaptureEnabled}
            onOpenTraceDialog={onOpenTraceDialog}
          />
          <section className="min-h-0 flex-1 overflow-y-auto pr-1">
            <div className="space-y-4">
              <div className="rounded-[24px] bg-[color:var(--surface-container-low)] px-4 py-3 shadow-[var(--panel-shadow)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                      {presentation.stageEyebrow}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <h2 className="text-sm font-semibold tracking-tight text-primary">
                        {presentation.stageTitle}
                      </h2>
                      <p className="text-xs text-on-surface-variant">{presentation.stageDescription}</p>
                    </div>
                  </div>
                  <div className="rounded-full bg-[color:var(--surface-container-lowest)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary shadow-[var(--panel-shadow)]">
                    {presentation.stageStatus}
                  </div>
                </div>
              </div>
              {isSearchAgent ? (
                <SearchBundlePanel
                  activeBundleId={activeBundleId}
                  error={bundleProposalError}
                  isLoading={isLoadingBundleProposals}
                  proposals={bundleProposals}
                />
              ) : (
                <>
                  {previewPanel}
                  {supportsImageAttachments ? attachmentPanel : null}
                </>
              )}
            </div>
          </section>
          {isTraceCaptureEnabled && threadId ? (
            <SaveTraceDialog
              agentName={currentAgent}
              onClose={onCloseTraceDialog}
              open={isTraceDialogOpen}
              threadId={threadId}
            />
          ) : null}
        </section>
        <aside
          className="min-h-[70vh] min-w-0 xl:min-h-0"
          {...(isSearchAgent ? { "data-testid": "search-chat-rail" } : {})}
        >
          <div className="flex h-full min-h-[70vh] min-w-0 flex-col xl:min-h-0">
            {chatPanel}
          </div>
        </aside>
      </section>
    </main>
  );
}
