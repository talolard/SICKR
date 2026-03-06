import { describe, expect, it } from "vitest";

import { getOrCreateSessionId } from "./sessionStore";

describe("getOrCreateSessionId", () => {
  it("creates and persists a new session id when missing", () => {
    const storage = window.localStorage;
    storage.clear();

    const sessionId = getOrCreateSessionId(storage);

    expect(sessionId).toHaveLength(36);
    expect(storage.getItem("ikea_agent_session_id")).toBe(sessionId);
  });

  it("reuses existing session id when present", () => {
    const storage = window.localStorage;
    storage.setItem("ikea_agent_session_id", "session-123");

    const sessionId = getOrCreateSessionId(storage);

    expect(sessionId).toBe("session-123");
  });
});
