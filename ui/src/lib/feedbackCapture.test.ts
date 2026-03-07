import { getConsoleRecordsSnapshot, startFeedbackCapture } from "@/lib/feedbackCapture";

describe("feedbackCapture", () => {
  it("captures console events into a bounded snapshot", () => {
    startFeedbackCapture();
    const before = getConsoleRecordsSnapshot().length;

    console.warn("feedback-test", { case: 1 });

    const after = getConsoleRecordsSnapshot();
    expect(after.length).toBeGreaterThanOrEqual(before + 1);
    expect(after.at(-1)?.level).toBe("warn");
    expect(after.at(-1)?.args[0]).toContain("feedback-test");
  });
});
