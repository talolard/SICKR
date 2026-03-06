"use client";

import { useEffect, useState } from "react";
import type { ReactElement } from "react";

import {
  getThreadDetail,
  listThreadAssets,
  type AssetListItem,
  type ThreadDetailItem,
} from "@/lib/api/threadDataClient";

type Props = {
  threadId: string;
};

export function ThreadDataPanel({ threadId }: Props): ReactElement {
  const [detail, setDetail] = useState<ThreadDetailItem | null>(null);
  const [assets, setAssets] = useState<AssetListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    Promise.all([getThreadDetail(threadId), listThreadAssets(threadId)])
      .then(([nextDetail, nextAssets]) => {
        if (!active) {
          return;
        }
        setDetail(nextDetail);
        setAssets(nextAssets);
      })
      .catch((requestError: unknown) => {
        if (!active) {
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
    return <p className="text-xs text-gray-500">Loading thread data...</p>;
  }

  return (
    <section className="rounded border border-gray-200 bg-white p-3 text-xs text-gray-700">
      <p className="font-medium text-gray-900">Thread data</p>
      <p>Title: {detail.title ?? "(untitled)"}</p>
      <p>Assets: {detail.asset_count}</p>
      <p>Floor-plan revisions: {detail.floor_plan_revision_count}</p>
      <p>Analyses: {detail.analysis_count}</p>
      <p>Search runs: {detail.search_count}</p>
      <p className="mt-2 font-medium text-gray-900">Latest assets</p>
      <ul className="list-disc pl-4">
        {assets.slice(0, 3).map((asset) => (
          <li key={asset.asset_id}>
            {asset.kind} · {asset.file_name ?? asset.asset_id}
          </li>
        ))}
      </ul>
    </section>
  );
}
