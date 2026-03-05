"use client";

import type { ReactElement } from "react";
import { useDefaultRenderTool, useRenderTool } from "@copilotkit/react-core/v2";
import { z } from "zod";

import { DefaultToolCallRenderer } from "@/components/tooling/DefaultToolCallRenderer";
import { ImageToolOutputRenderer } from "@/components/tooling/ImageToolOutputRenderer";
import { ProductResultsToolRenderer } from "@/components/tooling/ProductResultsToolRenderer";
import type { AttachmentRef } from "@/lib/attachments";
import { parseProductResults } from "@/lib/productResults";

type ImageToolOutput = {
  caption: string;
  images: AttachmentRef[];
};

const attachmentRefSchema = z.object({
  attachment_id: z.string(),
  mime_type: z.string(),
  uri: z.string(),
  width: z.number().nullable(),
  height: z.number().nullable(),
  file_name: z.string().nullable().optional(),
});

const imageToolOutputSchema = z.object({
  caption: z.string(),
  images: z.array(attachmentRefSchema),
});

type ParsedAttachmentRef = z.infer<typeof attachmentRefSchema>;

function parseResult(result: unknown): unknown {
  if (typeof result !== "string") {
    return result;
  }
  try {
    return JSON.parse(result) as unknown;
  } catch {
    return result;
  }
}

function normalizeAttachmentRef(parsed: ParsedAttachmentRef): AttachmentRef {
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

function parseAttachmentList(result: unknown): AttachmentRef[] | null {
  const parsed = parseResult(result);
  if (!Array.isArray(parsed)) {
    return null;
  }
  const validated = z.array(attachmentRefSchema).safeParse(parsed);
  return validated.success ? validated.data.map(normalizeAttachmentRef) : null;
}

function parseImageToolOutput(result: unknown): ImageToolOutput | null {
  const validated = imageToolOutputSchema.safeParse(parseResult(result));
  if (!validated.success) {
    return null;
  }
  return {
    caption: validated.data.caption,
    images: validated.data.images.map(normalizeAttachmentRef),
  };
}

export function CopilotToolRenderers(): ReactElement | null {
  useDefaultRenderTool({
    render: ({ name, status, result, parameters }) => {
      const parsedResult = parseResult(result);
      const mappedStatus =
        status === "inProgress" ? "queued" : status === "executing" ? "executing" : "complete";
      return (
        <div className="rounded border bg-white p-2">
          <DefaultToolCallRenderer
            name={name}
            status={mappedStatus}
            result={parsedResult}
            args={parameters}
            errorMessage={undefined}
          />
        </div>
      );
    },
  });

  useRenderTool({
    name: "run_search_graph",
    parameters: z.object({
      semantic_query: z.string(),
      limit: z.number().optional(),
      filters: z.unknown().optional(),
    }),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Searching IKEA catalog...</p>
          </div>
        );
      }
      const products = parseProductResults(result) ?? [];
      return (
        <div className="rounded border bg-white p-2">
          <ProductResultsToolRenderer products={products} />
        </div>
      );
    },
  });

  useRenderTool({
    name: "render_floor_plan",
    parameters: z.unknown(),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Rendering floor plan...</p>
          </div>
        );
      }
      const imageOutput = parseImageToolOutput(result);
      if (!imageOutput) {
        return (
          <div className="rounded border bg-white p-2">
            <DefaultToolCallRenderer
              name="render_floor_plan"
              status="complete"
              result={result}
              args={undefined}
              errorMessage={undefined}
            />
          </div>
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <ImageToolOutputRenderer caption={imageOutput.caption} images={imageOutput.images} />
        </div>
      );
    },
  });

  useRenderTool({
    name: "list_uploaded_images",
    parameters: z.object({}),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Inspecting uploaded images...</p>
          </div>
        );
      }
      const images = parseAttachmentList(result);
      if (!images) {
        return (
          <div className="rounded border bg-white p-2">
            <DefaultToolCallRenderer
              name="list_uploaded_images"
              status="complete"
              result={result}
              args={undefined}
              errorMessage={undefined}
            />
          </div>
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <ImageToolOutputRenderer caption="Uploaded images" images={images} />
        </div>
      );
    },
  });

  useRenderTool({
    name: "generate_floor_plan_preview_image",
    parameters: z.object({}),
    render: ({ status, result }) => {
      if (status !== "complete") {
        return (
          <div className="rounded border bg-white p-2">
            <p className="text-sm text-gray-700">Generating preview image...</p>
          </div>
        );
      }
      const imageOutput = parseImageToolOutput(result);
      if (!imageOutput) {
        return (
          <div className="rounded border bg-white p-2">
            <DefaultToolCallRenderer
              name="generate_floor_plan_preview_image"
              status="complete"
              result={result}
              args={undefined}
              errorMessage={undefined}
            />
          </div>
        );
      }
      return (
        <div className="rounded border bg-white p-2">
          <ImageToolOutputRenderer caption={imageOutput.caption} images={imageOutput.images} />
        </div>
      );
    },
  });

  return null;
}
