"use client";

import { useState, type ReactElement } from "react";

import type { AttachmentRef } from "@/lib/attachments";

type ImageAnalysisWorkspacePanelProps = {
  attachments: AttachmentRef[];
};

export function ImageAnalysisWorkspacePanel({
  attachments,
}: ImageAnalysisWorkspacePanelProps): ReactElement {
  const [selectedImage, setSelectedImage] = useState<AttachmentRef | null>(null);

  return (
    <section
      className="editorial-panel-elevated overflow-hidden rounded-[30px] p-4"
      data-testid="image-analysis-workspace-panel"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
            Room photo board
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold tracking-tight text-primary">Visual context</h2>
            <p className="max-w-2xl text-xs leading-5 text-on-surface-variant">
              Keep the uploaded room images visible while the agent extracts mood, objects, and
              styling opportunities.
            </p>
          </div>
        </div>
        <div className="rounded-full bg-[color:var(--tertiary-fixed)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">
          {attachments.length === 0 ? "Awaiting photos" : `${attachments.length} image${attachments.length === 1 ? "" : "s"} ready`}
        </div>
      </div>

      {attachments.length === 0 ? (
        <div className="relative mt-4 min-h-[22rem] overflow-hidden rounded-[28px] bg-[color:var(--surface-container-low)] p-6">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(130,84,41,0.12),transparent_26%),radial-gradient(circle_at_bottom_right,rgba(24,36,27,0.08),transparent_28%)]" />
          <div className="absolute inset-0 opacity-20 [background-image:radial-gradient(circle_at_center,rgba(32,27,16,0.45)_1px,transparent_1px)] [background-size:36px_36px]" />
          <div className="relative flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[color:var(--surface-container-lowest)] text-primary shadow-[var(--panel-shadow)]">
              <svg aria-hidden="true" className="h-7 w-7" fill="none" viewBox="0 0 20 20">
                <path
                  d="M5.2 6.2h2.1l1-1.4h3.4l1 1.4h2.1c1 0 1.9.8 1.9 1.9v5.7c0 1-.9 1.9-1.9 1.9H5.2c-1 0-1.9-.9-1.9-1.9V8.1c0-1.1.9-1.9 1.9-1.9Z"
                  stroke="currentColor"
                  strokeLinejoin="round"
                  strokeWidth="1.4"
                />
                <circle cx="10" cy="10.9" r="2.5" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            </div>
            <h3 className="mt-6 text-[1.4rem] font-semibold leading-tight tracking-tight text-primary">
              Upload room photos to start the review
            </h3>
            <p className="mt-3 max-w-xl text-sm leading-6 text-on-surface-variant">
              Once images are uploaded, this board becomes the stable visual reference for the
              consultation rail and analysis output.
            </p>
          </div>
        </div>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.28fr)_minmax(240px,0.72fr)]">
          <button
            className="group relative overflow-hidden rounded-[28px] bg-[color:var(--surface-container-low)] text-left shadow-[var(--panel-shadow)]"
            data-testid={`image-analysis-hero-${attachments[0]?.attachment_id}`}
            onClick={() => setSelectedImage(attachments[0] ?? null)}
            type="button"
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- Attachment previews may be runtime-generated or local files. */}
            <img
              alt={attachments[0]?.file_name ?? "Uploaded room image"}
              className="h-full min-h-[24rem] w-full object-cover transition duration-500 group-hover:scale-[1.02]"
              src={attachments[0]?.uri}
            />
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(32,27,16,0.06)_0%,rgba(32,27,16,0.44)_100%)]" />
            <div className="absolute bottom-5 left-5 rounded-[22px] bg-[rgba(255,255,255,0.92)] px-4 py-3 shadow-[var(--panel-shadow)]">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                Primary reference
              </p>
              <p className="mt-1.5 text-sm font-semibold text-primary">
                {attachments[0]?.file_name ?? "Uploaded room image"}
              </p>
            </div>
          </button>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            {attachments.slice(1).map((attachment) => (
              <button
                className="group overflow-hidden rounded-[24px] bg-[color:var(--surface-container-low)] text-left shadow-[var(--panel-shadow)]"
                data-testid={`image-analysis-thumb-${attachment.attachment_id}`}
                key={attachment.attachment_id}
                onClick={() => setSelectedImage(attachment)}
                type="button"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- Attachment previews may be runtime-generated or local files. */}
                <img
                  alt={attachment.file_name ?? "Uploaded room image"}
                  className="h-48 w-full object-cover transition duration-500 group-hover:scale-[1.02]"
                  src={attachment.uri}
                />
                <div className="px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                    Supporting angle
                  </p>
                  <p className="mt-1.5 text-sm font-semibold text-primary">
                    {attachment.file_name ?? "Uploaded room image"}
                  </p>
                </div>
              </button>
            ))}
            {attachments.length === 1 ? (
              <div className="rounded-[24px] bg-[color:var(--surface-container-low)] px-4 py-5 shadow-[var(--panel-shadow)]">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
                  Next step
                </p>
                <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                  Add another angle if you want the analysis to compare sight lines, furniture
                  groupings, or problem areas across the room.
                </p>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {selectedImage ? (
        <div
          className="fixed inset-0 z-[2100] flex items-center justify-center bg-black/70 p-6"
          data-testid="image-analysis-viewer-modal"
          onClick={() => setSelectedImage(null)}
        >
          <div
            className="max-w-[90vw] rounded-[28px] bg-[color:var(--surface-container-lowest)] p-4 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- Modal displays the original attachment URI unchanged. */}
            <img
              alt={selectedImage.file_name ?? "Uploaded room image"}
              className="max-h-[82vh] max-w-[88vw] rounded-[22px]"
              src={selectedImage.uri}
            />
            <div className="mt-4 flex justify-end">
              <button
                className="rounded-full bg-[color:var(--primary)] px-4 py-2 text-sm font-semibold text-white"
                onClick={() => setSelectedImage(null)}
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
