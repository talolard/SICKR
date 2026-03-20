"use client";

import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import {
  getThreadDetail,
  listThreadAssets,
  type AssetListItem,
  type ThreadDetailItem,
  ThreadDataRequestError,
} from "@/lib/api/threadDataClient";

type Props = {
  threadId: string;
};

export function ThreadDataPanel({ threadId }: Props): ReactElement {
  const [detail, setDetail] = useState<ThreadDetailItem | null>(null);
  const [assets, setAssets] = useState<AssetListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [missingThreadData, setMissingThreadData] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    Promise.all([getThreadDetail(threadId), listThreadAssets(threadId)])
      .then(([nextDetail, nextAssets]) => {
        if (!active) {
          return;
        }
        setError(null);
        setMissingThreadData(false);
        setDetail(nextDetail);
        setAssets(nextAssets);
      })
      .catch((requestError: unknown) => {
        if (!active) {
          return;
        }
        if (requestError instanceof ThreadDataRequestError && requestError.status === 404) {
          setMissingThreadData(true);
          return;
        }
        const message =
          requestError instanceof Error ? requestError.message : "Failed to load thread data.";
        setError(message);
      });
    return () => {
      active = false;
    };
  }, [threadId]);

  if (error) {
    return <p className="text-xs text-red-700">{error}</p>;
  }

  if (detail === null) {
    if (missingThreadData) {
      return <p className="text-xs text-on-surface-variant">Thread data will appear after the first save.</p>;
    }
    return <p className="text-xs text-on-surface-variant">Loading thread data...</p>;
  }

  return (
    <section className="rounded-[24px] bg-[color:var(--surface-container-lowest)] px-4 py-4 text-xs text-on-surface shadow-[var(--panel-shadow)]">
      <p className="editorial-eyebrow">Tracked thread</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Room" value={detail.room_title} />
        <MetricCard label="Room type" value={detail.room_type ?? "(unset)"} />
        <MetricCard label="Assets" value={String(detail.asset_count)} />
        <MetricCard label="Floor-plan revisions" value={String(detail.floor_plan_revision_count)} />
        <MetricCard label="Analyses" value={String(detail.analysis_count)} />
        <MetricCard label="Search runs" value={String(detail.search_count)} />
      </div>
      <div className="mt-4 rounded-[20px] bg-[color:var(--surface-container-low)] px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          Latest assets
        </p>
        <ul className="mt-2 space-y-2">
          {assets.slice(0, 3).map((asset) => (
            <li
              className="rounded-full bg-[color:var(--surface-container-lowest)] px-3 py-1.5"
              key={asset.asset_id}
            >
              {asset.display_label ?? asset.file_name ?? asset.asset_id}
            </li>
          ))}
          {assets.length === 0 ? (
            <li className="text-on-surface-variant">No saved assets yet.</li>
          ) : null}
        </ul>
      </div>
    </section>
  );
}

function MetricCard({ label, value }: { label: string; value: string }): ReactElement {
  return (
    <div className="rounded-[18px] bg-[color:var(--surface-container-low)] px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold text-primary">{value}</p>
    </div>
  );
}
