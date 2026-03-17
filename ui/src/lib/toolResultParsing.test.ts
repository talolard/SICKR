import { describe, expect, it } from "vitest";

import {
  extractToolFailureMessage,
  parseAttachmentList,
  parseImageToolOutput,
} from "./toolResultParsing";

describe("toolResultParsing", () => {
  it("unwraps image output payloads nested under return_value", () => {
    const parsed = parseImageToolOutput({
      return_value: {
        caption: "Draft floor plan",
        images: [
          {
            attachment_id: "generated-1",
            mime_type: "image/svg+xml",
            uri: "/attachments/generated-1",
            width: null,
            height: null,
          },
        ],
      },
    });

    expect(parsed).toEqual({
      caption: "Draft floor plan",
      images: [
        {
          attachment_id: "generated-1",
          mime_type: "image/svg+xml",
          uri: "/attachments/generated-1",
          width: null,
          height: null,
        },
      ],
    });
  });

  it("parses attachment lists for uploaded image tools", () => {
    const parsed = parseAttachmentList([
      {
        attachment_id: "upload-1",
        mime_type: "image/png",
        uri: "/attachments/upload-1",
        width: 640,
        height: 480,
        file_name: "room.png",
      },
    ]);

    expect(parsed).toEqual([
      {
        attachment_id: "upload-1",
        mime_type: "image/png",
        uri: "/attachments/upload-1",
        width: 640,
        height: 480,
        file_name: "room.png",
      },
    ]);
  });

  it("extracts structured tool failure messages", () => {
    expect(
      extractToolFailureMessage({
        status: "error",
        message: "Tool run failed.",
        reason: "missing image attachment",
      }),
    ).toBe("Tool run failed. (missing image attachment)");
  });
});
