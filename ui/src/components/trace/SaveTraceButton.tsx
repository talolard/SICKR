"use client";

import type { ReactElement } from "react";

type SaveTraceButtonProps = {
  onClick: () => void;
};

export function SaveTraceButton({ onClick }: SaveTraceButtonProps): ReactElement {
  return (
    <button
      aria-label="Save current trace"
      className="rounded border border-gray-300 px-2.5 py-1.5 text-sm text-gray-800 hover:bg-gray-50"
      onClick={onClick}
      title="Save current trace"
      type="button"
    >
      ⤓
    </button>
  );
}
