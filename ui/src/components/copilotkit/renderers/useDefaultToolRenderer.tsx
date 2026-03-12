"use client";

import { useDefaultRenderTool } from "@copilotkit/react-core/v2";

import {
  extractToolFailureMessage,
  looksLikeToolFailure,
  parseResult,
} from "@/lib/toolResultParsing";

import { DefaultToolCard, mapCopilotToolStatus } from "./shared";

export function useDefaultToolRenderer(): void {
  useDefaultRenderTool({
    render: ({ name, status, result, parameters }) => {
      const parsedResult = parseResult(result);
      const mappedStatusBase = mapCopilotToolStatus(status);
      const mappedStatus =
        mappedStatusBase === "complete" && looksLikeToolFailure(parsedResult)
          ? "failed"
          : mappedStatusBase;
      const failureMessage = extractToolFailureMessage(parsedResult);
      return (
        <DefaultToolCard
          name={name}
          status={mappedStatus}
          result={mappedStatus === "failed" ? undefined : parsedResult}
          args={parameters}
          errorMessage={mappedStatus === "failed" ? failureMessage : undefined}
        />
      );
    },
  });
}
