"use client";

import { useState } from "react";
import type { ReactElement } from "react";

import type { AttachmentRef } from "@/lib/attachments";

type ImageToolOutputRendererProps = {
  caption: string;
  images: AttachmentRef[];
};

export function ImageToolOutputRenderer({
  caption,
  images,
}: ImageToolOutputRendererProps): ReactElement {
  const [selectedImage, setSelectedImage] = useState<AttachmentRef | null>(null);

  return (
    <section className="rounded-[22px] bg-[color:var(--surface-container-low)] p-3" data-testid="image-tool-output">
      <p className="editorial-eyebrow">Image output</p>
      <p className="mt-2 text-sm font-semibold text-primary">{caption}</p>
      <div className="mt-3 flex flex-wrap gap-3">
        {images.map((image) => (
          <button
            data-testid={`image-thumb-${image.attachment_id}`}
            key={image.attachment_id}
            onClick={() => setSelectedImage(image)}
            type="button"
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- Attachment thumbnails may point to runtime-generated blob/data URLs. */}
            <img
              alt={image.file_name ?? "Generated image"}
              className="h-24 w-24 rounded-[18px] object-cover shadow-[var(--panel-shadow)]"
              loading="lazy"
              src={image.uri}
            />
          </button>
        ))}
      </div>
      {selectedImage ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
          data-testid="image-viewer-modal"
        >
          <div className="max-w-4xl rounded-[28px] bg-[color:var(--surface-container-lowest)] p-4">
            {/* eslint-disable-next-line @next/next/no-img-element -- Modal displays exact attachment bytes without image optimization transforms. */}
            <img
              alt={selectedImage.file_name ?? "Generated image"}
              className="max-h-[70vh] max-w-[80vw] rounded-[20px]"
              src={selectedImage.uri}
            />
            <div className="mt-3 flex gap-2">
              <a
                className="rounded-full bg-[color:var(--surface-container-low)] px-4 py-2 text-sm font-semibold text-primary"
                download={selectedImage.file_name ?? "generated-image"}
                href={selectedImage.uri}
              >
                Download
              </a>
              <a
                className="rounded-full bg-[color:var(--surface-container-low)] px-4 py-2 text-sm font-semibold text-primary"
                href={selectedImage.uri}
                rel="noreferrer"
                target="_blank"
              >
                Open in new tab
              </a>
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
