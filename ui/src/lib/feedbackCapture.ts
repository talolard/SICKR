export type FeedbackConsoleEntry = {
  timestamp: string;
  level: "log" | "info" | "warn" | "error";
  args: string[];
};

const MAX_CONSOLE_RECORDS = 250;
const records: FeedbackConsoleEntry[] = [];
let installed = false;

function toSerializableArg(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function pushRecord(level: FeedbackConsoleEntry["level"], args: unknown[]): void {
  records.push({
    timestamp: new Date().toISOString(),
    level,
    args: args.map(toSerializableArg),
  });
  if (records.length > MAX_CONSOLE_RECORDS) {
    records.splice(0, records.length - MAX_CONSOLE_RECORDS);
  }
}

function installConsoleCapture(): void {
  if (installed || typeof window === "undefined") {
    return;
  }
  installed = true;

  const originalLog = window.console.log.bind(window.console);
  const originalInfo = window.console.info.bind(window.console);
  const originalWarn = window.console.warn.bind(window.console);
  const originalError = window.console.error.bind(window.console);

  window.console.log = (...args: unknown[]): void => {
    pushRecord("log", args);
    originalLog(...args);
  };
  window.console.info = (...args: unknown[]): void => {
    pushRecord("info", args);
    originalInfo(...args);
  };
  window.console.warn = (...args: unknown[]): void => {
    pushRecord("warn", args);
    originalWarn(...args);
  };
  window.console.error = (...args: unknown[]): void => {
    pushRecord("error", args);
    originalError(...args);
  };

  window.addEventListener("error", (event) => {
    pushRecord("error", [event.message]);
  });
  window.addEventListener("unhandledrejection", (event) => {
    pushRecord("error", ["unhandledrejection", toSerializableArg(event.reason)]);
  });
}

export function startFeedbackCapture(): void {
  installConsoleCapture();
}

export function getConsoleRecordsSnapshot(): FeedbackConsoleEntry[] {
  return [...records];
}
