import { z } from "zod";

import type { AttachmentRef } from "@/lib/attachments";

export const attachmentRefSchema = z.object({
  attachment_id: z.string(),
  mime_type: z.string(),
  uri: z.string(),
  width: z.number().nullable(),
  height: z.number().nullable(),
  file_name: z.string().nullable().optional(),
});

export type ParsedAttachmentRef = z.infer<typeof attachmentRefSchema>;

export type ImageToolOutput = {
  caption: string;
  images: AttachmentRef[];
};

export const imageToolOutputSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
});

export function unwrapToolReturnValue(result: unknown): unknown {
  if (typeof result !== "object" || result === null) {
    return result;
  }
  if ("return_value" in result) {
    return (result as { return_value: unknown }).return_value;
  }
  if ("result" in result) {
    return (result as { result: unknown }).result;
  }
  return result;
}

export function parseResult(result: unknown): unknown {
  if (typeof result !== "string") {
    return unwrapToolReturnValue(result);
  }
  try {
    return unwrapToolReturnValue(JSON.parse(result) as unknown);
  } catch {
    return result;
  }
}

export function normalizeAttachmentRef(parsed: ParsedAttachmentRef): AttachmentRef {
  const normalized: AttachmentRef = {
    attachment_id: parsed.attachment_id,
    mime_type: parsed.mime_type,
    uri: parsed.uri,
    width: parsed.width,
    height: parsed.height,
  };
  if (parsed.file_name !== undefined) {
    normalized.file_name = parsed.file_name;
  }
  return normalized;
}

export function parseAttachmentList(result: unknown): AttachmentRef[] | null {
  const parsed = parseResult(result);
  if (!Array.isArray(parsed)) {
    return null;
  }
  const validated = z.array(attachmentRefSchema).safeParse(parsed);
  return validated.success ? validated.data.map(normalizeAttachmentRef) : null;
}

export function parseImageToolOutput(result: unknown): ImageToolOutput | null {
  const validated = imageToolOutputSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
  };
}

export function looksLikeToolFailure(result: unknown): result is string {
  const parsed = parseResult(result);
  if (
    typeof parsed === "object" &&
    parsed !== null &&
    "status" in parsed &&
    parsed.status === "error"
  ) {
    return true;
  }
  if (typeof parsed !== "string") {
    return false;
  }
  return (
    /validation errors?/i.test(parsed) ||
    /tool failed/i.test(parsed) ||
    /missing_terminal_event/i.test(parsed) ||
    /terminated/i.test(parsed)
  );
}

export function extractToolFailureMessage(result: unknown): string | undefined {
  const parsed = parseResult(result);
  if (
    typeof parsed === "object" &&
    parsed !== null &&
    "status" in parsed &&
    parsed.status === "error"
  ) {
    const message =
      "message" in parsed && typeof parsed.message === "string"
        ? parsed.message
        : "Tool run failed.";
    const reason =
      "reason" in parsed && typeof parsed.reason === "string"
        ? parsed.reason
        : undefined;
    return reason ? `${message} (${reason})` : message;
  }
  if (typeof parsed === "string" && looksLikeToolFailure(parsed)) {
    return parsed;
  }
  return undefined;
}
