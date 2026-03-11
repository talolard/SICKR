import type { ReactElement } from "react";
import { parseProductResults } from "../../lib/productResults";

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
  const searchQueries =
    name === "run_search_graph" &&
    typeof args === "object" &&
    args !== null &&
    "queries" in args &&
    Array.isArray(args.queries)
      ? args.queries
          .flatMap((query) => {
            if (typeof query !== "object" || query === null || !("semantic_query" in query)) {
              return [];
            }
            return typeof query.semantic_query === "string" ? [query.semantic_query] : [];
          })
          .filter((query) => query.length > 0)
      : [];
  const productCount =
    name === "run_search_graph" && status !== "failed"
      ? (parseProductResults(result)?.length ?? 0)
      : null;

  if (status === "failed") {
    return (
      <section aria-label={`tool-${name}`}>
        <h2>{name}</h2>
        <p>Status: failed</p>
        {searchQueries.length > 0 ? <p>Search queries: {searchQueries.join(" · ")}</p> : null}
        <p>Action: Retry with updated input.</p>
        {errorMessage ? <pre>{errorMessage}</pre> : null}
      </section>
    );
  }

  return (
    <section aria-label={`tool-${name}`}>
      <h2>{name}</h2>
      <p>Status: {status}</p>
      {searchQueries.length > 0 ? <p>Search queries: {searchQueries.join(" · ")}</p> : null}
      {productCount !== null ? <p>Result count: {productCount}</p> : null}
      {productCount === null && result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
    </section>
  );
}

export type { ToolCallStatus, DefaultToolCallRendererProps };
