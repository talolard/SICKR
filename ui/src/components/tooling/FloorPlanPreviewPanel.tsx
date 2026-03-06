"use client";

import { useMemo, useState } from "react";
import type { ReactElement } from "react";

import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";

type FloorPlanPreviewPanelProps = {
  preview: FloorPlanPreviewState | null;
};

export function FloorPlanPreviewPanel({
  preview,
}: FloorPlanPreviewPanelProps): ReactElement {
  const [selectedUri, setSelectedUri] = useState<string | null>(null);

  const primaryImage = useMemo(() => {
    if (!preview) {
      return null;
    }
    const svg = preview.images.find((image) => image.mime_type === "image/svg+xml");
    return svg ?? preview.images[0] ?? null;
  }, [preview]);

  if (!preview || !primaryImage) {
    return (
      <section className="rounded-lg border bg-white p-4">
        <h2 className="text-lg font-semibold text-gray-900">Floor Plan Preview</h2>
        <p className="mt-2 text-sm text-gray-600">
          Render a floor plan to see the latest layout here.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Floor Plan Preview</h2>
          <p className="mt-1 text-xs text-gray-500">
            Revision {preview.sceneRevision} · {preview.sceneLevel}
          </p>
        </div>
        <button
          className="rounded border px-3 py-1 text-xs text-gray-700 hover:bg-gray-50"
          onClick={() => setSelectedUri(primaryImage.uri)}
          type="button"
        >
          Open large view
        </button>
      </div>

      <div className="mt-3 flex items-center justify-center rounded border bg-gray-50 p-3">
        <img
          alt="Latest floor plan"
          className="max-h-[72vh] w-full max-w-[980px] object-contain"
          src={primaryImage.uri}
        />
      </div>

      <p className="mt-3 text-sm text-gray-700">{preview.caption}</p>

      {preview.warnings.length > 0 ? (
        <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2">
          <p className="text-xs font-semibold text-amber-900">Warnings</p>
          {preview.warnings.slice(0, 4).map((warning) => (
            <p className="mt-1 text-xs text-amber-900" key={`${warning.code}-${warning.message}`}>
              {warning.code}: {warning.message}
            </p>
          ))}
        </div>
      ) : null}

      {selectedUri ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6">
          <div className="max-w-[90vw] rounded bg-white p-4">
            <img alt="Floor plan full view" className="max-h-[82vh] max-w-[88vw]" src={selectedUri} />
            <div className="mt-3 flex justify-end">
              <button
                className="rounded border px-3 py-1 text-sm"
                onClick={() => setSelectedUri(null)}
                type="button"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
