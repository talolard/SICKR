"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ForwardRefExoticComponent,
  PropsWithoutRef,
  ReactElement,
  RefAttributes,
} from "react";

import type { FloorPlanScene } from "@/lib/floorPlanScene";
import type { FloorPlanPreviewState } from "@/lib/floorPlanPreviewStore";
import type { Room3DSnapshotContext } from "@/lib/threadStore";
import type { FloorPlanScene3DHandle, FloorPlanScene3DSnapshot } from "./FloorPlanScene3D";

type FloorPlanScene3DProps = {
  scene: FloorPlanScene;
};

type FloorPlanScene3DComponent = ForwardRefExoticComponent<
  PropsWithoutRef<FloorPlanScene3DProps> & RefAttributes<FloorPlanScene3DHandle>
>;

type FloorPlanPreviewPanelProps = {
  preview: FloorPlanPreviewState | null;
  scene3dOverride?: FloorPlanScene3DComponent;
  onSnapshotCaptured?: (
    snapshot: Omit<Room3DSnapshotContext, "snapshot_id" | "attachment"> & {
      image_data_url: string;
    },
  ) => Promise<void>;
};

export function FloorPlanPreviewPanel({
  preview,
  onSnapshotCaptured,
  scene3dOverride,
}: FloorPlanPreviewPanelProps): ReactElement {
  const [selectedUri, setSelectedUri] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"2d" | "3d">("2d");
  const [snapshotComment, setSnapshotComment] = useState<string>("");
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState<boolean>(false);
  const [Scene3D, setScene3D] = useState<FloorPlanScene3DComponent | null>(null);
  const [isScene3dReady, setIsScene3dReady] = useState<boolean>(false);
  const scene3dRef = useRef<FloorPlanScene3DHandle | null>(null);

  const primaryImage = useMemo(() => {
    if (!preview) {
      return null;
    }
    const svg = preview.images.find((image) => image.mime_type === "image/svg+xml");
    return svg ?? preview.images[0] ?? null;
  }, [preview]);

  const shouldLoad3d = activeTab === "3d" && Boolean(preview?.scene);

  useEffect(() => {
    if (!shouldLoad3d || Scene3D) {
      return;
    }
    if (scene3dOverride) {
      setScene3D(() => scene3dOverride);
      return;
    }
    let cancelled = false;
    void import("./FloorPlanScene3D").then((module) => {
      if (cancelled) {
        return;
      }
      setScene3D(() => module.FloorPlanScene3D as unknown as FloorPlanScene3DComponent);
    });
    return () => {
      cancelled = true;
    };
  }, [Scene3D, scene3dOverride, shouldLoad3d]);

  useEffect(() => {
    if (!shouldLoad3d || !Scene3D) {
      setIsScene3dReady(false);
      return;
    }
    setIsScene3dReady(scene3dRef.current !== null);
  }, [Scene3D, shouldLoad3d]);

  if (!preview || !primaryImage) {
    return (
      <section className="editorial-panel-elevated overflow-hidden rounded-[30px] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
              Floor plan preview
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold tracking-tight text-primary">
                Drafting surface
              </h2>
              <p className="text-xs leading-5 text-on-surface-variant">
                Render a floor plan to see the latest layout and dimensional notes here.
              </p>
            </div>
          </div>
          <div className="rounded-full bg-[color:var(--tertiary-fixed)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
            Awaiting first layout
          </div>
        </div>
        <div className="relative mt-4 min-h-[24rem] overflow-hidden rounded-[28px] bg-[color:var(--surface-container-low)] p-6">
          <div className="pointer-events-none absolute inset-0 opacity-[0.18] [background-image:radial-gradient(circle_at_center,rgba(32,27,16,0.45)_1px,transparent_1px)] [background-size:34px_34px]" />
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(130,84,41,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(24,36,27,0.08),transparent_30%)]" />
          <div className="relative flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[color:var(--surface-container-lowest)] text-primary shadow-[var(--panel-shadow)]">
              <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 20 20">
                <path
                  d="M4.5 14.8h11M5.8 14.8V5.6l4.2-2.8 4.2 2.8v9.2"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1.4"
                />
                <path d="M10 7.4v7.4" stroke="currentColor" strokeLinecap="round" strokeWidth="1.4" />
              </svg>
            </div>
            <h3 className="mt-6 text-[1.4rem] font-semibold leading-tight tracking-tight text-primary">
              Render a layout to activate the workbench
            </h3>
            <p className="mt-3 max-w-xl text-sm leading-6 text-on-surface-variant">
              Once a layout is rendered, the drafting surface will show the current revision in 2D
              and 3D without leaving this page.
            </p>
          </div>
        </div>
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
    <section className="editorial-panel-elevated overflow-hidden rounded-[30px] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
            Floor plan preview
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight text-primary">Current layout</h2>
            <p className="text-xs leading-5 text-on-surface-variant">
              Revision {preview.sceneRevision} · {preview.sceneLevel}
            </p>
          </div>
        </div>
        <button
          className="rounded-full bg-[color:var(--surface-container-low)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-primary"
          onClick={() => setSelectedUri(primaryImage.uri)}
          type="button"
        >
          Open large view
        </button>
      </div>

      <div
        className="mt-4 inline-flex rounded-full bg-[color:var(--surface-container-low)] p-1 text-xs shadow-[var(--panel-shadow)]"
        role="tablist"
      >
        <button
          aria-selected={activeTab === "2d"}
          className={`rounded-full px-3 py-1.5 ${
            activeTab === "2d"
              ? "bg-[color:var(--surface-container-lowest)] text-primary shadow-[var(--panel-shadow)]"
              : "text-on-surface-variant"
          }`}
          onClick={() => setActiveTab("2d")}
          role="tab"
          type="button"
        >
          2D
        </button>
        <button
          aria-selected={activeTab === "3d"}
          className={`rounded-full px-3 py-1.5 ${
            activeTab === "3d"
              ? "bg-[color:var(--surface-container-lowest)] text-primary shadow-[var(--panel-shadow)]"
              : "text-on-surface-variant"
          }`}
          onClick={() => setActiveTab("3d")}
          role="tab"
          type="button"
        >
          3D
        </button>
      </div>

      {activeTab === "2d" ? (
        <div className="relative mt-4 flex min-h-[28rem] items-center justify-center overflow-hidden rounded-[28px] bg-[color:var(--surface-container-low)] p-4">
          <div className="pointer-events-none absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_center,rgba(32,27,16,0.45)_1px,transparent_1px)] [background-size:34px_34px]" />
          {/* eslint-disable-next-line @next/next/no-img-element -- Floor plan previews can be local data/blob URIs. */}
          <img
            alt="Latest floor plan"
            className="relative h-full max-h-[70vh] w-full rounded-[22px] bg-[color:var(--surface-container-lowest)] object-contain p-2 shadow-[0_30px_60px_rgba(32,27,16,0.08)]"
            src={primaryImage.uri}
          />
        </div>
      ) : preview.scene ? (
        <div className="mt-4 space-y-3">
          {Scene3D ? (
            <Scene3D ref={scene3dRef} scene={preview.scene} />
          ) : (
            <div className="flex h-[54vh] items-center justify-center rounded-[28px] bg-[color:var(--surface-container-low)] text-sm text-on-surface-variant">
              Loading 3D scene...
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded-full bg-[color:var(--surface-container-low)] px-3 py-1.5 text-xs font-semibold text-primary"
              disabled={!isScene3dReady}
              onClick={() => scene3dRef.current?.resetOverview()}
              type="button"
            >
              Overview
            </button>
            <button
              className="rounded-full bg-[color:var(--surface-container-low)] px-3 py-1.5 text-xs font-semibold text-primary"
              disabled={!isScene3dReady}
              onClick={() => scene3dRef.current?.setInteriorView()}
              type="button"
            >
              Enter room
            </button>
          </div>
          <p className="text-xs text-on-surface-variant" data-testid="scene-units-caption">
            Units note: scene geometry keeps centimeter relationships and renders in meters.
          </p>
          <p className="text-xs text-[#7a4f23]" data-testid="lighting-emphasis-caption">
            Lighting emphasis markers: {lightFixtureCount} fixture
            {lightFixtureCount === 1 ? "" : "s"} highlighted.
          </p>
          <div className="space-y-3 rounded-[24px] bg-[color:var(--surface-container-low)] p-4">
            <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-on-surface-variant" htmlFor="snapshot-comment">
              Snapshot comment (optional)
            </label>
            <textarea
              className="w-full rounded-[20px] bg-[color:var(--surface-container-lowest)] p-3 text-sm"
              id="snapshot-comment"
              onChange={(event) => setSnapshotComment(event.target.value)}
              placeholder="What should the agent focus on in this perspective?"
              value={snapshotComment}
            />
            <div className="flex flex-wrap items-center gap-2">
              <button
                className="rounded-full bg-[color:var(--primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                disabled={isCapturing || !onSnapshotCaptured || !isScene3dReady}
                onClick={() => {
                  void captureSnapshot();
                }}
                type="button"
              >
                {isCapturing ? "Capturing..." : "Capture PNG"}
              </button>
              {captureError ? (
                <button
                  className="rounded-full bg-red-50 px-4 py-2 text-sm font-semibold text-red-700"
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
          className="mt-4 rounded-[24px] bg-amber-50 px-4 py-4 text-sm text-amber-900"
          data-testid="floor-plan-3d-empty"
        >
          3D scene data is not available for this revision yet.
        </div>
      )}

      <p className="mt-4 text-sm leading-6 text-on-surface">{preview.caption}</p>

      {preview.warnings.length > 0 ? (
        <div className="mt-3 rounded-[24px] bg-amber-50 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-900">
            Warnings
          </p>
          {preview.warnings.slice(0, 4).map((warning) => (
            <p className="mt-2 text-xs leading-5 text-amber-900" key={`${warning.code}-${warning.message}`}>
              {warning.code}: {warning.message}
            </p>
          ))}
        </div>
      ) : null}

      {selectedUri ? (
        <div
          className="fixed inset-0 z-[2100] flex items-center justify-center bg-black/70 p-6"
          data-testid="floor-plan-backdrop"
          onClick={() => setSelectedUri(null)}
        >
          <div
            className="max-w-[90vw] rounded-[28px] bg-[color:var(--surface-container-lowest)] p-4 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- Modal keeps original image bytes for export/debug parity. */}
            <img
              alt="Floor plan full view"
              className="max-h-[82vh] max-w-[88vw] rounded-[22px]"
              src={selectedUri}
            />
            <div className="mt-3 flex justify-end">
              <button
                className="rounded-full bg-[color:var(--primary)] px-4 py-2 text-sm font-semibold text-white"
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
