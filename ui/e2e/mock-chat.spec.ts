import { expect, test } from "@playwright/test";

const HARNESS_URL = "/debug/agui-harness?mock=1";

test("streams assistant text from mock AG-UI route", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await expect(page.getByRole("heading", { name: "AG-UI Streaming Harness" })).toBeVisible();
  await expect(page.getByText("Chat")).toBeVisible();
  await page.getByTestId("send-button").click();
  await expect(page.getByText("You")).toBeVisible();
  await expect(page.getByText("Assistant")).toBeVisible();
  await expect(page.getByTestId("assistant-text")).toContainText("Analyzing request...");
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
  await expect(
    page.getByText("Search query: Find me storage for a small bedroom"),
  ).toBeVisible();
  await expect(page.getByText("Result count: 1")).toBeVisible();
});

test("renders tool status transitions executing -> complete", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("tool-status")).toContainText("complete");
});

test("shows retry UI when stream disconnects and retry succeeds", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("scenario-select").selectOption("disconnect");
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("stream-error")).toContainText(
    "Stream ended unexpectedly",
  );
  await page.getByTestId("retry-button").click();
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
});

test("blocks send while attachment upload is pending and unblocks when done", async ({
  page,
}) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("attachment-input").setInputFiles({
    name: "room.png",
    mimeType: "image/png",
    buffer: Buffer.from([1, 2, 3, 4, 5]),
  });

  await expect(page.getByTestId("pending-upload-warning")).toBeVisible();
  await expect(page.getByTestId("send-button")).toBeDisabled();
  await expect(page.getByTestId("attachment-list")).toContainText("ready");
  await expect(page.getByTestId("send-button")).toBeEnabled();
});

test("retries failed send without re-uploading attachments", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("attachment-input").setInputFiles({
    name: "room.png",
    mimeType: "image/png",
    buffer: Buffer.from([1, 2, 3, 4, 5, 6]),
  });
  await expect(page.getByTestId("attachment-list")).toContainText("ready");

  await page.getByTestId("scenario-select").selectOption("send_fail_once");
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("stream-error")).toContainText(
    "Temporary upstream send failure",
  );
  await expect(page.getByTestId("attachment-list")).toContainText("ready");

  await page.getByTestId("retry-button").click();
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Using 1 uploaded image(s).",
  );
});

test("renders generated image output and opens viewer modal", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("image-tool-output")).toBeVisible();
  await page.getByTestId("image-thumb-generated-1").click();
  await expect(page.getByTestId("image-viewer-modal")).toBeVisible();
  await page.getByText("Close").click();
  await expect(page.getByTestId("image-viewer-modal")).toBeHidden();
});

test("shows progress updates for long-running tool calls", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("scenario-select").selectOption("long_running");
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("run-status-container")).toContainText("Working...");
  await expect(page.getByTestId("tool-progress-tool-1")).toContainText(
    "Searching catalog:",
  );
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
});

test("cancels long-running run locally and notifies user", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("scenario-select").selectOption("long_running");
  await page.getByTestId("send-button").click();
  await page.getByTestId("cancel-button").click();
  await expect(page.getByTestId("stream-error")).toContainText("Run canceled locally.");
});

test("persists thread history across refresh", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
  const threadId = await page.getByTestId("thread-id").textContent();
  await page.reload();
  await expect(page.getByTestId("thread-id")).toContainText(threadId ?? "");
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
});

test("isolates thread history when switching to a new thread", async ({ page }) => {
  await page.goto(HARNESS_URL);
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
  const previousThreadId = (await page.getByTestId("thread-id").textContent()) ?? "";
  await page.getByTestId("new-thread-button").click();
  await expect(page.getByTestId("assistant-text")).toHaveText("");
  await expect(page.getByTestId("thread-id")).not.toContainText(previousThreadId);
  await page.goto(`${HARNESS_URL}&thread=${previousThreadId}`);
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
});

test("opens save-trace dialog on the agent page and saves with recent traces", async ({ page }) => {
  await page.route("**/api/traces/recent?limit=5", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        traces: [
          {
            trace_id: "trace-old",
            title: "Earlier trace",
            created_at: "2026-03-11T10:00:00Z",
            directory: "/tmp/traces/trace-old",
            markdown_path: "/tmp/traces/trace-old/report.md",
          },
        ],
      }),
    });
  });
  await page.route("**/api/traces", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        trace_id: "trace-new",
        directory: "/tmp/traces/trace-new",
        trace_json_path: "/tmp/traces/trace-new/trace.json",
        markdown_path: "/tmp/traces/trace-new/report.md",
        beads_epic_id: "epic-1",
        beads_task_id: "epic-1.1",
        status: "saved_and_linked",
      }),
    });
  });

  await page.goto("/agents/search");
  await expect(page.getByLabel("Save current trace")).toBeVisible();
  await page.getByLabel("Save current trace").click();
  await expect(page.getByText("Recent traces")).toBeVisible();
  await expect(page.getByText("Earlier trace")).toBeVisible();
  await page.getByLabel("Title").fill("Regression trace");
  await page.getByRole("button", { name: "Save trace" }).click();
  await expect(page.getByText(/Saved trace trace-new and created epic-1/)).toBeVisible();
  await expect(page.getByText("/tmp/traces/trace-new")).toBeVisible();
});

test("shows partial-success save-trace messaging when Beads creation fails", async ({ page }) => {
  await page.route("**/api/traces/recent?limit=5", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ traces: [] }),
    });
  });
  await page.route("**/api/traces", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        trace_id: "trace-partial",
        directory: "/tmp/traces/trace-partial",
        trace_json_path: "/tmp/traces/trace-partial/trace.json",
        markdown_path: "/tmp/traces/trace-partial/report.md",
        status: "saved_without_beads",
      }),
    });
  });

  await page.goto("/agents/search");
  await page.getByLabel("Save current trace").click();
  await page.getByLabel("Title").fill("Regression partial trace");
  await page.getByRole("button", { name: "Save trace" }).click();

  await expect(
    page.getByText(/Saved trace trace-partial at \/tmp\/traces\/trace-partial, but Beads creation did not complete\./),
  ).toBeVisible();
});
