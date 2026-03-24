type LogLevel = "info" | "error";

type LogFields = Record<string, unknown>;

export function runtimeMetadata(): { environment: string; release_version: string } {
  return {
    environment:
      process.env.APP_ENV ?? process.env.LOGFIRE_ENVIRONMENT ?? process.env.NODE_ENV ?? "development",
    release_version: process.env.APP_RELEASE_VERSION ?? process.env.LOGFIRE_SERVICE_VERSION ?? "dev",
  };
}

export function logServerRouteEvent(level: LogLevel, event: string, fields: LogFields = {}): void {
  const payload = JSON.stringify({
    event,
    ...runtimeMetadata(),
    ...fields,
  });
  if (level === "error") {
    console.error(payload);
    return;
  }
  console.info(payload);
}
