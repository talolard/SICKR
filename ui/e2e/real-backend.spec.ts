import { HttpAgent } from "@ag-ui/client";
import { expect, test } from "@playwright/test";

function shouldRunRealBackendSuite(): boolean {
  return process.env.RUN_REAL_BACKEND_E2E === "1";
}

test.describe("real backend smoke", () => {
  test.skip(!shouldRunRealBackendSuite(), "Set RUN_REAL_BACKEND_E2E=1 to enable.");

  test("streams assistant response from mounted Python AG-UI endpoint", async () => {
    test.setTimeout(90_000);
    const agUiUrl = process.env.PY_AG_UI_URL ?? "http://127.0.0.1:8000/ag-ui/";
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
    expect(JSON.stringify(latestAssistant)).toContain("IKEA");
  });
});
