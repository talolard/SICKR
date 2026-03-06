const SESSION_KEY = "ikea_agent_session_id";

export function getOrCreateSessionId(storage: Storage): string {
  const existing = storage.getItem(SESSION_KEY);
  if (existing && existing.trim().length > 0) {
    return existing;
  }
  const generated = crypto.randomUUID();
  storage.setItem(SESSION_KEY, generated);
  return generated;
}
