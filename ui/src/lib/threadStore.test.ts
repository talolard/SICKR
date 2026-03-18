import { beforeEach, describe, expect, it } from "vitest";

import {
  loadResumableThreadIds,
  loadRoom3DSnapshots,
  loadThreadIds,
  loadActiveThreadId,
  loadThreadSnapshot,
  saveResumableThreadIds,
  saveRoom3DSnapshots,
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
      copilotMessages: [
        {
          id: "msg-1",
          createdAt: "2026-03-18T10:00:00Z",
          content: "hello",
          role: "user",
        },
      ],
    });

    expect(loadActiveThreadId()).toBe("thread-1");
    expect(loadThreadSnapshot("thread-1")?.assistantText).toBe("world");
    expect(loadThreadSnapshot("thread-1")?.copilotMessages).toHaveLength(1);
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

  it("persists room 3d snapshot context per thread", () => {
    saveRoom3DSnapshots("thread-1", [
      {
        snapshot_id: "snap-1",
        attachment: {
          attachment_id: "asset-1",
          mime_type: "image/png",
          uri: "/attachments/asset-1",
          width: null,
          height: null,
          file_name: "snapshot.png",
        },
        comment: "focus on ceiling lights",
        captured_at: "2026-03-06T22:00:00Z",
        camera: {
          position_m: [1, 1.5, 2],
          target_m: [1, 0.8, 1],
          fov_deg: 55,
        },
        lighting: {
          light_fixture_ids: ["light-1"],
          emphasized_light_count: 1,
        },
      },
    ]);

    const loaded = loadRoom3DSnapshots("thread-1");
    expect(loaded).toHaveLength(1);
    expect(loaded[0]?.snapshot_id).toBe("snap-1");
    expect(loaded[0]?.comment).toContain("ceiling");
  });
});
