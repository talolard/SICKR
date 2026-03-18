"use client";

import { useEffect, useRef, useState, type ReactElement } from "react";

type ProductImageThumbnailProps = {
  images: readonly string[];
  productName: string;
  testIdPrefix: string;
};

export function ProductImageThumbnail({
  images,
  productName,
  testIdPrefix,
}: ProductImageThumbnailProps): ReactElement {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const hasImages = images.length > 0;
  const selectedImage = hasImages ? images[selectedIndex] ?? images[0] : null;

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent): void {
      if (rootRef.current?.contains(event.target as Node)) {
        return;
      }
      setIsOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (!hasImages) {
    return (
      <div
        className="flex h-24 w-24 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-100 px-2 text-center text-xs font-medium text-gray-500"
        data-testid={`${testIdPrefix}-placeholder`}
      >
        Image pending
      </div>
    );
  }

  return (
    <div className="relative shrink-0" ref={rootRef}>
      <button
        className="group relative block h-24 w-24 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm"
        data-testid={`${testIdPrefix}-button`}
        onClick={() => {
          setSelectedIndex(0);
          setIsOpen((current) => !current);
        }}
        type="button"
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- Runtime-served local catalog images should bypass Next optimization. */}
        <img
          alt={`${productName} thumbnail`}
          className="h-full w-full object-cover transition group-hover:scale-[1.02]"
          loading="lazy"
          src={images[0]}
        />
        {images.length > 1 ? (
          <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
            +{images.length - 1}
          </span>
        ) : null}
      </button>
      {isOpen && selectedImage ? (
        <div
          aria-label={`${productName} image gallery`}
          className="absolute left-0 top-full z-30 mt-2 w-80 rounded-xl border border-gray-200 bg-white p-3 shadow-2xl"
          data-testid={`${testIdPrefix}-popover`}
          role="dialog"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- Runtime-served local catalog images should bypass Next optimization. */}
          <img
            alt={`${productName} image ${selectedIndex + 1}`}
            className="h-56 w-full rounded-lg object-cover"
            src={selectedImage}
          />
          <div className="mt-2 flex items-center justify-between gap-2">
            <p className="text-xs font-medium text-gray-600">
              Image {selectedIndex + 1} of {images.length}
            </p>
            <div className="flex gap-2">
              <a
                className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700"
                href={selectedImage}
                rel="noreferrer"
                target="_blank"
              >
                Open in new tab
              </a>
              <button
                className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700"
                onClick={() => setIsOpen(false)}
                type="button"
              >
                Close
              </button>
            </div>
          </div>
          {images.length > 1 ? (
            <>
              <div className="mt-3 flex items-center justify-between gap-2">
                <button
                  className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700"
                  onClick={() => {
                    setSelectedIndex((current) =>
                      current === 0 ? images.length - 1 : current - 1
                    );
                  }}
                  type="button"
                >
                  Previous
                </button>
                <button
                  className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700"
                  onClick={() => {
                    setSelectedIndex((current) =>
                      current === images.length - 1 ? 0 : current + 1
                    );
                  }}
                  type="button"
                >
                  Next
                </button>
              </div>
              <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
                {images.map((image, index) => (
                  <button
                    className={`h-14 w-14 shrink-0 overflow-hidden rounded-md border ${
                      index === selectedIndex
                        ? "border-gray-900 ring-1 ring-gray-900"
                        : "border-gray-200"
                    }`}
                    data-testid={`${testIdPrefix}-thumb-${index + 1}`}
                    key={image}
                    onClick={() => setSelectedIndex(index)}
                    type="button"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element -- Runtime-served local catalog images should bypass Next optimization. */}
                    <img
                      alt={`${productName} thumbnail ${index + 1}`}
                      className="h-full w-full object-cover"
                      src={image}
                    />
                  </button>
                ))}
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
