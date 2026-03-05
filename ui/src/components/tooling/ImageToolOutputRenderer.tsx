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
    <section className="mt-2 rounded border p-2" data-testid="image-tool-output">
      <p className="text-sm font-medium">{caption}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {images.map((image) => (
          <button
            data-testid={`image-thumb-${image.attachment_id}`}
            key={image.attachment_id}
            onClick={() => setSelectedImage(image)}
            type="button"
          >
            <img
              alt={image.file_name ?? "Generated image"}
              className="h-24 w-24 rounded border object-cover"
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
          <div className="max-w-4xl rounded bg-white p-4">
            <img
              alt={selectedImage.file_name ?? "Generated image"}
              className="max-h-[70vh] max-w-[80vw]"
              src={selectedImage.uri}
            />
            <div className="mt-3 flex gap-2">
              <a
                className="rounded border px-3 py-1 text-sm"
                download={selectedImage.file_name ?? "generated-image"}
                href={selectedImage.uri}
              >
                Download
              </a>
              <a
                className="rounded border px-3 py-1 text-sm"
                href={selectedImage.uri}
                rel="noreferrer"
                target="_blank"
              >
                Open in new tab
              </a>
              <button
                className="rounded border px-3 py-1 text-sm"
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
