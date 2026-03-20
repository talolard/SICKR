import { expect, test } from "@playwright/test";

const HARNESS_URL = "/debug/agui-harness?mock=1";
const SEEDED_SEARCH_THREAD_ID = "mock-seeded-search-thread";
const SEEDED_BUNDLE_PROPOSAL = {
  bundle_id: "bundle-1",
  title: "Desk setup",
  notes:
    "Portable lighting for the hallway without drilling. Use adhesive-friendly pieces and keep the explanation fully visible.",
  budget_cap_eur: 200,
  items: [
    {
      item_id: "chair-1",
      product_name: "Chair One",
      display_title: "Chair One Ergonomic Desk Chair",
      product_url: "https://www.ikea.com/de/de/p/chair-one-12345678/",
      description_text: "Desk chair",
      price_eur: 79.99,
      quantity: 2,
      line_total_eur: 159.98,
      reason: "Two matching chairs",
      image_urls: [],
    },
  ],
  bundle_total_eur: 159.98,
  validations: [
    {
      kind: "pricing_complete",
      status: "pass",
      message: "All bundle items have prices, so the total is complete.",
    },
    {
      kind: "duplicate_items",
      status: "warn",
      message: "Merged 1 repeated product entry into combined quantities.",
    },
  ],
  created_at: "2026-03-11T11:00:00Z",
  run_id: "run-1",
};

function seedSearchBundleStateScript(): string {
  return `
    (() => {
      const threadId = ${JSON.stringify(SEEDED_SEARCH_THREAD_ID)};
      localStorage.setItem("copilotkit_ui_active_thread_agent_search", threadId);
      localStorage.setItem("copilotkit_ui_thread_ids_agent_search", JSON.stringify([threadId]));
      sessionStorage.setItem(
        "copilotkit_ui_resumable_thread_ids_tmp_agent_search",
        JSON.stringify([threadId]),
      );
      localStorage.setItem(
        "copilotkit_ui_bundle_proposals_" + threadId,
        JSON.stringify([${JSON.stringify(SEEDED_BUNDLE_PROPOSAL)}]),
      );
    })();
  `;
}

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
    page.getByText("Search queries: Find me storage for a small bedroom"),
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

test("keeps the home launcher rails aligned at canonical desktop width", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1200 });
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Welcome to your Designer's Studio" }),
  ).toBeVisible();
  await expect(page.getByTestId("studio-showcase-left-rail")).toBeVisible();
  await expect(page.getByTestId("studio-showcase-right-rail")).toBeVisible();
  await expect(page.getByRole("button", { name: "View All Archives" })).toBeVisible();

  const metrics = await page.evaluate(() => {
    const leftRail = document.querySelector(
      "[data-testid='studio-showcase-left-rail']",
    ) as HTMLElement | null;
    const rightRail = document.querySelector(
      "[data-testid='studio-showcase-right-rail']",
    ) as HTMLElement | null;

    return {
      leftHeight: leftRail?.getBoundingClientRect().height ?? 0,
      leftTop: leftRail?.getBoundingClientRect().top ?? 0,
      rightHeight: rightRail?.getBoundingClientRect().height ?? 0,
      rightTop: rightRail?.getBoundingClientRect().top ?? 0,
      viewportHeight: window.innerHeight,
    };
  });

  expect(Math.abs(metrics.leftTop - metrics.rightTop)).toBeLessThanOrEqual(4);
  expect(metrics.leftHeight).toBeGreaterThan(metrics.viewportHeight * 0.75);
  expect(metrics.rightHeight).toBeGreaterThan(metrics.viewportHeight * 0.75);
});

test("keeps the home launcher coherent at narrower desktop widths", async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 1100 });
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Welcome to your Designer's Studio" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "My Designs" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Search workspace/i })).toBeVisible();
  await expect(page.getByRole("button", { name: "View All Archives" })).toBeVisible();
  await expect(page.getByTestId("studio-showcase-left-rail")).toBeVisible();
  await expect(page.getByTestId("studio-showcase-right-rail")).toBeHidden();
});
test("keeps active-thread search pages compact and hides pass-state validations", async ({
  page,
}) => {
  await page.addInitScript(seedSearchBundleStateScript());
  await page.goto(`/agents/search?thread=${SEEDED_SEARCH_THREAD_ID}`);

  await expect(page.getByRole("heading", { name: "Search" })).toBeVisible();
  await expect(page.getByText("Desk setup")).toBeVisible();
  await expect(page.getByText("Find products that fit your style, budget, and room needs.")).toHaveCount(0);

  const threadDataDisclosure = page.locator("details", {
    has: page.getByText("Thread data"),
  });
  await expect(threadDataDisclosure).not.toHaveAttribute("open", "");

  const bundleToggle = page.getByRole("button", { name: /Desk setup/i });
  await bundleToggle.click();
  await expect(page.getByText(/Duplicates:/)).toBeVisible();
  await expect(page.getByText(/Pricing:/)).toHaveCount(0);
});
