import type { ReactElement } from "react";

type CopilotChatInlineErrorProps = {
  message: string;
  onDismiss: () => void;
  onRetry?: (() => void) | undefined;
  operation?: string | undefined;
};

export function CopilotChatInlineError({
  message,
  onDismiss,
  onRetry,
  operation,
}: CopilotChatInlineErrorProps): ReactElement {
  return (
    <section
      aria-live="polite"
      className="mx-3 mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900"
      role="alert"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-semibold">This request failed.</p>
          <p className="mt-1 break-words">{message}</p>
          {operation ? <p className="mt-1 text-xs text-red-700">Operation: {operation}</p> : null}
        </div>
        <button
          className="shrink-0 rounded border border-red-300 px-2 py-1 text-xs font-medium text-red-800 hover:bg-red-100"
          onClick={onDismiss}
          type="button"
        >
          Dismiss
        </button>
      </div>
      {onRetry ? (
        <button
          className="mt-3 rounded border border-red-300 px-3 py-1.5 text-xs font-medium text-red-800 hover:bg-red-100"
          onClick={onRetry}
          type="button"
        >
          Retry
        </button>
      ) : null}
    </section>
  );
}
