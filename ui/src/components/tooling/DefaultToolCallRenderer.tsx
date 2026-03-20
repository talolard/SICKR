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
      <section aria-label={`tool-${name}`} className="min-w-0 space-y-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
            Tool call
          </p>
          <h2 className="mt-1 text-sm font-semibold text-primary">{name}</h2>
        </div>
        <p className="text-sm leading-6 text-on-surface-variant">Status: failed</p>
        {searchQueries.length > 0 ? <p>Search queries: {searchQueries.join(" · ")}</p> : null}
        <p className="text-sm leading-6 text-on-surface-variant">Action: Retry with updated input.</p>
        {errorMessage ? (
          <pre className="overflow-hidden whitespace-pre-wrap break-words rounded-[18px] bg-[color:var(--surface-container-low)] px-3 py-3 text-xs leading-6 text-on-surface-variant">
            {errorMessage}
          </pre>
        ) : null}
      </section>
    );
  }

  return (
    <section aria-label={`tool-${name}`} className="min-w-0 space-y-3">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-on-surface-variant">
          Tool call
        </p>
        <h2 className="mt-1 text-sm font-semibold text-primary">{name}</h2>
      </div>
      <p className="text-sm leading-6 text-on-surface-variant">Status: {status}</p>
      {searchQueries.length > 0 ? (
        <p className="text-sm leading-6 text-on-surface-variant">
          Search queries: {searchQueries.join(" · ")}
        </p>
      ) : null}
      {productCount !== null ? (
        <p className="text-sm leading-6 text-on-surface-variant">Result count: {productCount}</p>
      ) : null}
      {productCount === null && result ? (
        <pre className="overflow-hidden whitespace-pre-wrap break-words rounded-[18px] bg-[color:var(--surface-container-low)] px-3 py-3 text-xs leading-6 text-on-surface-variant">
          {JSON.stringify(result, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}

export type { ToolCallStatus, DefaultToolCallRendererProps };
