"use client";

import { useMemo, useState } from "react";
import type { ReactElement } from "react";
import { useRef } from "react";

import {
  FloorPlanScene3D,
  type FloorPlanScene3DHandle,
  type FloorPlanScene3DSnapshot,
} from "@/components/tooling/FloorPlanScene3D";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import type { Room3DSnapshotContext } from "@/lib/threadStore";

type FloorPlanPreviewPanelProps = {
  preview: FloorPlanPreviewState | null;
  onSnapshotCaptured?: (
    snapshot: Omit<Room3DSnapshotContext, "snapshot_id" | "attachment"> & {
      image_data_url: string;
    },
  ) => Promise<void>;
};

export function FloorPlanPreviewPanel({
  preview,
  onSnapshotCaptured,
}: FloorPlanPreviewPanelProps): ReactElement {
  const [selectedUri, setSelectedUri] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"2d" | "3d">("2d");
  const [snapshotComment, setSnapshotComment] = useState<string>("");
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const scene3dRef = useRef<FloorPlanScene3DHandle | null>(null);

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

  const lightFixtureCount =
    preview.scene?.scene_level === "detailed"
      ? (preview.scene.fixtures ?? []).filter((fixture) => fixture.fixture_kind === "light")
          .length
      : 0;

  const captureSnapshot = async (): Promise<void> => {
    if (!preview?.scene || !onSnapshotCaptured) {
      return;
    }
    setCaptureError(null);
    setIsCapturing(true);
    try {
      const captured: FloorPlanScene3DSnapshot | undefined = scene3dRef.current?.capturePng();
      if (!captured) {
        throw new Error("3D camera is not ready yet.");
      }
      await onSnapshotCaptured({
        image_data_url: captured.image_data_url,
        comment: snapshotComment.trim() || null,
        captured_at: captured.captured_at,
        camera: captured.camera,
        lighting: captured.lighting,
      });
      setSnapshotComment("");
    } catch (error) {
      setCaptureError(
        error instanceof Error ? error.message : "Snapshot capture failed unexpectedly.",
      );
    } finally {
      setIsCapturing(false);
    }
  };

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

      <div className="mt-3 inline-flex rounded border bg-gray-100 p-1 text-xs" role="tablist">
        <button
          aria-selected={activeTab === "2d"}
          className={`rounded px-2.5 py-1 ${activeTab === "2d" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600"}`}
          onClick={() => setActiveTab("2d")}
          role="tab"
          type="button"
        >
          2D
        </button>
        <button
          aria-selected={activeTab === "3d"}
          className={`rounded px-2.5 py-1 ${activeTab === "3d" ? "bg-white text-gray-900 shadow-sm" : "text-gray-600"}`}
          onClick={() => setActiveTab("3d")}
          role="tab"
          type="button"
        >
          3D
        </button>
      </div>

      {activeTab === "2d" ? (
        <div className="mt-3 flex h-[76vh] items-center justify-center rounded border bg-gray-50 p-1">
          <img
            alt="Latest floor plan"
            className="h-full w-full object-contain"
            src={primaryImage.uri}
          />
        </div>
      ) : preview.scene ? (
        <div className="mt-3 space-y-2">
          <FloorPlanScene3D ref={scene3dRef} scene={preview.scene} />
          <div className="flex items-center gap-2">
            <button
              className="rounded border border-gray-300 px-2.5 py-1 text-xs text-gray-800 hover:bg-gray-50"
              onClick={() => scene3dRef.current?.resetOverview()}
              type="button"
            >
              Overview
            </button>
            <button
              className="rounded border border-gray-300 px-2.5 py-1 text-xs text-gray-800 hover:bg-gray-50"
              onClick={() => scene3dRef.current?.setInteriorView()}
              type="button"
            >
              Enter room
            </button>
          </div>
          <p className="text-xs text-gray-600" data-testid="scene-units-caption">
            Units note: scene geometry keeps centimeter relationships and renders in meters.
          </p>
          <p className="text-xs text-amber-800" data-testid="lighting-emphasis-caption">
            Lighting emphasis markers: {lightFixtureCount} fixture
            {lightFixtureCount === 1 ? "" : "s"} highlighted.
          </p>
          <div className="space-y-2 rounded border border-gray-200 p-2">
            <label className="block text-xs text-gray-700" htmlFor="snapshot-comment">
              Snapshot comment (optional)
            </label>
            <textarea
              className="w-full rounded border border-gray-300 p-2 text-sm"
              id="snapshot-comment"
              onChange={(event) => setSnapshotComment(event.target.value)}
              placeholder="What should the agent focus on in this perspective?"
              value={snapshotComment}
            />
            <div className="flex items-center gap-2">
              <button
                className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-800 hover:bg-gray-50 disabled:opacity-60"
                disabled={isCapturing || !onSnapshotCaptured}
                onClick={() => {
                  void captureSnapshot();
                }}
                type="button"
              >
                {isCapturing ? "Capturing..." : "Capture PNG"}
              </button>
              {captureError ? (
                <button
                  className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-700"
                  onClick={() => {
                    void captureSnapshot();
                  }}
                  type="button"
                >
                  Retry capture
                </button>
              ) : null}
            </div>
            {captureError ? (
              <p className="text-xs text-red-700" data-testid="snapshot-capture-error">
                {captureError}
              </p>
            ) : null}
          </div>
        </div>
      ) : (
        <div
          className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
          data-testid="floor-plan-3d-empty"
        >
          3D scene data is not available for this revision yet.
        </div>
      )}

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
        <div
          className="fixed inset-0 z-[2100] flex items-center justify-center bg-black/70 p-6"
          onClick={() => setSelectedUri(null)}
          data-testid="floor-plan-backdrop"
        >
          <div
            className="max-w-[90vw] rounded bg-white p-4 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <img alt="Floor plan full view" className="max-h-[82vh] max-w-[88vw]" src={selectedUri} />
            <div className="mt-3 flex justify-end">
              <button
                className="rounded border bg-white px-3 py-1 text-sm shadow-sm"
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
