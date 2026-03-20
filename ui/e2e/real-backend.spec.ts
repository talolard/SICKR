import { HttpAgent } from "@ag-ui/client";
import { expect, test } from "@playwright/test";

function shouldRunRealBackendSuite(): boolean {
  return process.env.RUN_REAL_BACKEND_E2E === "1";
}

function expectedSmokeAssistantText(): string | null {
  const text = process.env.E2E_SMOKE_ASSISTANT_TEXT;
  return text && text.length > 0 ? text : null;
}

const SEEDED_SEARCH_THREAD_ID = "e2e-search-thread";
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
  ],
  created_at: "2026-03-11T11:00:00Z",
  run_id: "run-1",
};

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
    test.setTimeout(45_000);

    await page.goto("/agents/search");

    const chatInput = page.getByPlaceholder("Type a message...");
    const sendButton = page.getByRole("button", { name: "Send" });
    await expect(chatInput).toBeVisible();

    const prompt = "Give one short sentence recommending an IKEA storage item.";
    await chatInput.click();
    await chatInput.pressSequentially(prompt);
    await expect(sendButton).toBeEnabled({ timeout: 10_000 });
    await sendButton.click();
    await expect(chatInput).toHaveValue("", { timeout: 10_000 });

    const expectedText = expectedSmokeAssistantText();
    if (expectedText) {
      const deterministicResponse = page
        .locator(".agent-chat-pane .copilotKitAssistantMessage")
        .filter({ hasText: expectedText });
      await expect(deterministicResponse).toBeVisible({ timeout: 15_000 });
      return;
    }

    const assistantMessages = page.locator(".agent-chat-pane .copilotKitAssistantMessage");
    await expect
      .poll(async () => await assistantMessages.count(), { timeout: 20_000 })
      .toBeGreaterThan(0);
  });

  test("creates a fresh thread on search and floor-plan agent pages", async ({ page }) => {
    test.setTimeout(120_000);

    for (const agentName of ["search", "floor_plan_intake"] as const) {
      await page.goto(`/agents/${agentName}`);
      await expect(page.getByTestId("agent-thread-select")).toBeVisible();
      const previousThreadId = await page.getByTestId("agent-thread-select").inputValue();

      await page.getByTestId("new-thread-button").click();

      await expect(page.getByTestId("agent-thread-select")).not.toHaveValue(previousThreadId);
      await expect(page.getByTestId("agent-chat-sidebar")).toBeVisible();
      await expect(page).toHaveURL(/thread=/);
    }
  });

  test("keeps the search chat rail bounded when long content is injected", async ({ page }) => {
    test.setTimeout(120_000);

    await page.goto("/agents/search");
    await expect(page.getByTestId("agent-chat-sidebar")).toBeVisible();

    const pageScrollHeightBefore = await page.evaluate(() => document.documentElement.scrollHeight);

    await page.evaluate(() => {
      const container = document.querySelector(
        ".agent-chat-pane .copilotKitMessagesContainer",
      ) as HTMLElement | null;
      if (!container) {
        throw new Error("Could not find the chat messages container.");
      }

      const filler = document.createElement("div");
      filler.setAttribute("data-testid", "e2e-long-chat-block");
      filler.style.height = "2400px";
      filler.style.padding = "16px";
      filler.style.border = "1px solid rgb(203 213 225)";
      filler.style.borderRadius = "16px";
      filler.style.background = "rgb(248 250 252)";
      filler.textContent = "long transcript content ".repeat(300);
      container.appendChild(filler);
      container.scrollTop = container.scrollHeight;
    });

    const layoutMetrics = await page.evaluate(() => {
      const rail = document.querySelector("[data-testid='search-chat-rail']") as HTMLElement | null;
      const container = document.querySelector(
        ".agent-chat-pane .copilotKitMessagesContainer",
      ) as HTMLElement | null;
      return {
        pageScrollHeight: document.documentElement.scrollHeight,
        railHeight: rail?.getBoundingClientRect().height ?? 0,
        viewportHeight: window.innerHeight,
        containerClientHeight: container?.clientHeight ?? 0,
        containerScrollHeight: container?.scrollHeight ?? 0,
      };
    });

    expect(layoutMetrics.containerScrollHeight).toBeGreaterThan(layoutMetrics.containerClientHeight);
    expect(layoutMetrics.pageScrollHeight - pageScrollHeightBefore).toBeLessThan(200);
    expect(layoutMetrics.railHeight).toBeLessThan(layoutMetrics.viewportHeight);
  });

  test("keeps bundles collapsible and inspector debug details secondary on real pages", async ({
    page,
  }) => {
    test.setTimeout(120_000);

    await page.addInitScript(seedSearchBundleStateScript());
    await page.goto(`/agents/search?thread=${SEEDED_SEARCH_THREAD_ID}`);

    const bundleToggle = page.getByRole("button", { name: /Desk setup/i });
    await expect(page.getByTestId("search-bundle-panel-root")).toBeVisible();
    await expect(page.getByTestId("agent-inspector-debug-details")).not.toHaveAttribute("open", "");
    await expect(bundleToggle).toHaveAttribute("aria-expanded", "false");

    await bundleToggle.click();

    await expect(bundleToggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByTestId("bundle-items-bundle-1")).toBeVisible();

    await bundleToggle.click();

    await expect(bundleToggle).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByTestId("bundle-items-bundle-1")).toHaveCount(0);
  });

  test("navigates between agent workspaces from the launcher", async ({ page }) => {
    test.setTimeout(120_000);

    await page.goto("/agents/search");
    await page.getByTestId("app-nav-agent-launcher-trigger").click();
    await page.getByRole("button", { name: /Floor Plan Intake/i }).click();

    await expect(page).toHaveURL(/\/agents\/floor_plan_intake/);
    await expect(page.locator("h1")).toHaveText("Floor Plan Intake");
    await expect(page.getByTestId("agent-thread-select")).toBeVisible();
  });
});
