import { HttpAgent } from "@ag-ui/client";
import { expect, test } from "@playwright/test";

function shouldRunRealBackendSuite(): boolean {
  return process.env.RUN_REAL_BACKEND_E2E === "1";
}

function resolveAgentUrl(): string {
  const configuredUrl = process.env.PY_AG_UI_URL ?? "http://127.0.0.1:8000/ag-ui";
  const normalizedUrl = configuredUrl.endsWith("/")
    ? configuredUrl.slice(0, -1)
    : configuredUrl;
  if (normalizedUrl.includes("/agents/")) {
    return normalizedUrl;
  }
  return `${normalizedUrl}/agents/search`;
}

test.describe("real backend smoke", () => {
  test.skip(!shouldRunRealBackendSuite(), "Set RUN_REAL_BACKEND_E2E=1 to enable.");

  test("streams assistant response from mounted Python AG-UI endpoint", async () => {
    test.setTimeout(90_000);
    const agUiUrl = resolveAgentUrl();
    const agent = new HttpAgent({ url: agUiUrl });
    agent.addMessage({
      id: crypto.randomUUID(),
      role: "user",
      content: "Give one short sentence recommending an IKEA storage item.",
    });
    const result = await agent.runAgent();

    const assistantMessages = result.newMessages.filter(
      (message) => message.role === "assistant",
    );
    expect(assistantMessages.length).toBeGreaterThan(0);
    const latestAssistant = assistantMessages.at(-1);
    expect(latestAssistant).toBeDefined();
    const assistantPayload = JSON.stringify(latestAssistant);
    expect(assistantPayload.length).toBeGreaterThan(40);
  });

  test("sends and receives messages via CopilotKit UI", async ({ page }) => {
    test.setTimeout(120_000);

    await page.goto("/agents/search");
    const chatInput = page.getByPlaceholder("Type a message...");
    const sendButton = page.getByRole("button", { name: "Send" });
    await expect(chatInput).toBeVisible();
    await page.waitForTimeout(2_000);

    const prompt = "Give one short sentence recommending an IKEA storage item.";
    await chatInput.click();
    await chatInput.pressSequentially(prompt);
    await expect(sendButton).toBeEnabled({ timeout: 10_000 });
    await sendButton.click();
    await expect(chatInput).toHaveValue("", { timeout: 10_000 });
    const disabledMessage =
      "Live model requests are disabled. Set ALLOW_MODEL_REQUESTS=1 and GEMINI_API_KEY/GOOGLE_API_KEY for real responses.";
    await expect
      .poll(
        async () => ((await page.locator("body").textContent()) ?? "").includes(disabledMessage),
        { timeout: 60_000 },
      )
      .toBe(true);
  });
});
