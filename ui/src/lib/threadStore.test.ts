import { beforeEach, describe, expect, it } from "vitest";

import {
  loadActiveThreadId,
  loadThreadSnapshot,
  saveActiveThreadId,
  saveThreadSnapshot,
} from "./threadStore";

describe("threadStore", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("persists active thread id and snapshots", () => {
    saveActiveThreadId("thread-1");
    saveThreadSnapshot({
      threadId: "thread-1",
      prompt: "hello",
      assistantText: "world",
      toolCallsById: {},
      attachments: [],
    });

    expect(loadActiveThreadId()).toBe("thread-1");
    expect(loadThreadSnapshot("thread-1")?.assistantText).toBe("world");
  });
});
