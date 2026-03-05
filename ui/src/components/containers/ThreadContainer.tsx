import type { ReactElement } from "react";

type ThreadContainerProps = {
  threadId: string;
  onNewThread: () => void;
};

export function ThreadContainer({
  threadId,
  onNewThread,
}: ThreadContainerProps): ReactElement {
  return (
    <section className="flex items-center justify-between rounded border p-3">
      <div>
        <p className="text-xs text-gray-700">Thread</p>
        <p className="font-mono text-sm" data-testid="thread-id">
          {threadId}
        </p>
      </div>
      <button
        className="rounded border px-3 py-1 text-sm"
        data-testid="new-thread-button"
        onClick={onNewThread}
        type="button"
      >
        New thread
      </button>
    </section>
  );
}
