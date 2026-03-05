import type { ReactElement } from "react";

type ToolCallStatus = "queued" | "executing" | "complete" | "failed";

type DefaultToolCallRendererProps = {
  name: string;
  status: ToolCallStatus;
  result: unknown | undefined;
  errorMessage: string | undefined;
};

export function DefaultToolCallRenderer(
  props: DefaultToolCallRendererProps,
): ReactElement {
  const { name, status, result, errorMessage } = props;

  if (status === "failed") {
    return (
      <section aria-label={`tool-${name}`}>
        <h2>{name}</h2>
        <p>Status: failed</p>
        <p>Action: Retry with updated input.</p>
        {errorMessage ? <pre>{errorMessage}</pre> : null}
      </section>
    );
  }

  return (
    <section aria-label={`tool-${name}`}>
      <h2>{name}</h2>
      <p>Status: {status}</p>
      {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </section>
  );
}

export type { ToolCallStatus, DefaultToolCallRendererProps };
