import type { ToolCallStatus } from "@/components/tooling/DefaultToolCallRenderer";

export type ToolEventPayload = {
  tool_call_id: string;
  tool: string;
  status: ToolCallStatus;
  result: unknown | undefined;
  errorMessage: string | undefined;
};

export type ToolCallEntry = {
  id: string;
  name: string;
  status: ToolCallStatus;
  result: unknown | undefined;
  errorMessage: string | undefined;
};

export function upsertToolCall(
  current: Record<string, ToolCallEntry>,
  event: ToolEventPayload,
): Record<string, ToolCallEntry> {
  const previous = current[event.tool_call_id];
  return {
    ...current,
    [event.tool_call_id]: {
      id: event.tool_call_id,
      name: event.tool,
      status: event.status,
      result: event.result ?? previous?.result,
      errorMessage: event.errorMessage ?? previous?.errorMessage,
    },
  };
}
