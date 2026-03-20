import type { ReactElement, ReactNode } from "react";

import { DefaultToolCallRenderer } from "@/components/tooling/DefaultToolCallRenderer";

export type CopilotHookStatus = "inProgress" | "executing" | "complete";
export type CopilotToolRenderStatus = "queued" | "executing" | "complete";

type DefaultToolCardProps = {
  name: string;
  status: CopilotToolRenderStatus | "failed";
  result: unknown;
  args: unknown;
  errorMessage?: string | undefined;
};

type ToolCardProps = {
  children: ReactNode;
};

type LoadingToolMessageProps = {
  message: string;
};

export function mapCopilotToolStatus(status: CopilotHookStatus): CopilotToolRenderStatus {
  if (status === "inProgress") {
    return "queued";
  }
  if (status === "executing") {
    return "executing";
  }
  return "complete";
}

export function ToolCard({ children }: ToolCardProps): ReactElement {
  return (
    <div className="rounded-[24px] bg-[color:var(--surface-container-lowest)] p-3 shadow-[var(--panel-shadow)]">
      {children}
    </div>
  );
}

export function LoadingToolMessage({ message }: LoadingToolMessageProps): ReactElement {
  return (
    <ToolCard>
      <p className="text-sm leading-6 text-on-surface-variant">{message}</p>
    </ToolCard>
  );
}

export function DefaultToolCard({
  name,
  status,
  result,
  args,
  errorMessage,
}: DefaultToolCardProps): ReactElement {
  return (
    <ToolCard>
      <DefaultToolCallRenderer
        name={name}
        status={status}
        result={result}
        args={args}
        errorMessage={errorMessage}
      />
    </ToolCard>
  );
}
