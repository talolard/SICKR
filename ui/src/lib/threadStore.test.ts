import { beforeEach, describe, expect, it } from "vitest";

import {
  loadResumableThreadIds,
  loadThreadIds,
  loadActiveThreadId,
  loadThreadSnapshot,
  saveResumableThreadIds,
  saveThreadIds,
  saveActiveThreadId,
  saveThreadSnapshot,
  upsertThreadId,
} from "./threadStore";

describe("threadStore", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
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

  it("upserts thread ids without duplicates", () => {
    expect(upsertThreadId("thread-1")).toEqual(["thread-1"]);
    expect(upsertThreadId("thread-2")).toEqual(["thread-2", "thread-1"]);
    expect(upsertThreadId("thread-1")).toEqual(["thread-2", "thread-1"]);
  });

  it("loads and saves thread id indexes and resumable ids", () => {
    saveThreadIds(["thread-1", "thread-2"]);
    saveResumableThreadIds(["thread-2"]);

    expect(loadThreadIds()).toEqual(["thread-1", "thread-2"]);
    expect(loadResumableThreadIds()).toEqual(["thread-2"]);
  });
});
