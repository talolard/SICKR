import type { ReactElement } from "react";

type ToolProgress = {
  percent: number;
  label: string;
};

type RunStatusContainerProps = {
  isRunning: boolean;
  runningToolCount: number;
  toolProgressById: Record<string, ToolProgress>;
};

export function RunStatusContainer({
  isRunning,
  runningToolCount,
  toolProgressById,
}: RunStatusContainerProps): ReactElement {
  if (!isRunning && Object.keys(toolProgressById).length === 0) {
    return <></>;
  }
  return (
    <section className="rounded border p-3" data-testid="run-status-container">
      <p className="text-sm font-medium">{isRunning ? "Working..." : "Run complete"}</p>
      <p className="text-xs text-gray-700">{runningToolCount} tools running</p>
      <div className="mt-2 space-y-2">
        {Object.entries(toolProgressById).map(([toolCallId, progress]) => (
          <div data-testid={`tool-progress-${toolCallId}`} key={toolCallId}>
            <p className="text-xs">
              {progress.label}: {progress.percent}%
            </p>
            <div className="h-2 rounded bg-gray-200">
              <div
                className="h-2 rounded bg-blue-500"
                style={{ width: `${Math.min(100, Math.max(0, progress.percent))}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
