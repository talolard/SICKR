import type { ReactElement } from "react";

type ToolCallStatus = "queued" | "executing" | "complete" | "failed";

type DefaultToolCallRendererProps = {
  name: string;
  status: ToolCallStatus;
  result: unknown | undefined;
  args: unknown | undefined;
  errorMessage: string | undefined;
};

export function DefaultToolCallRenderer(
  props: DefaultToolCallRendererProps,
): ReactElement {
  const { name, status, result, args, errorMessage } = props;
  const semanticQuery =
    name === "run_search_graph" &&
    typeof args === "object" &&
    args !== null &&
    "semantic_query" in args &&
    typeof args.semantic_query === "string"
      ? args.semantic_query
      : null;

  if (status === "failed") {
    return (
      <section aria-label={`tool-${name}`}>
        <h2>{name}</h2>
        <p>Status: failed</p>
        {semanticQuery ? <p>Search query: {semanticQuery}</p> : null}
        <p>Action: Retry with updated input.</p>
        {errorMessage ? <pre>{errorMessage}</pre> : null}
      </section>
    );
  }

  return (
    <section aria-label={`tool-${name}`}>
      <h2>{name}</h2>
      <p>Status: {status}</p>
      {semanticQuery ? <p>Search query: {semanticQuery}</p> : null}
      {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </section>
  );
}

export type { ToolCallStatus, DefaultToolCallRendererProps };
