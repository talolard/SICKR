import { expect, test } from "@playwright/test";

test("streams assistant text from mock AG-UI route", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("assistant-text")).toContainText("Analyzing request...");
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
});

test("renders tool status transitions executing -> complete", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("tool-status")).toContainText("executing");
  await expect(page.getByTestId("tool-status")).toContainText("complete");
});

test("shows retry UI when stream disconnects and retry succeeds", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("scenario-select").selectOption("disconnect");
  await page.getByTestId("send-button").click();
  await expect(page.getByTestId("stream-error")).toContainText(
    "Stream ended unexpectedly",
  );
  await page.getByTestId("retry-button").click();
  await expect(page.getByTestId("tool-status")).toContainText("complete");
  await expect(page.getByTestId("assistant-text")).toContainText(
    "Found 3 matching products.",
  );
});
