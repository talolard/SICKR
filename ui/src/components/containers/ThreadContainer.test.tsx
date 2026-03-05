import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { ThreadContainer } from "./ThreadContainer";

describe("ThreadContainer", () => {
  it("renders current thread id and handles new thread action", () => {
    const onNewThread = vi.fn();
    render(<ThreadContainer onNewThread={onNewThread} threadId="thread-123" />);

    expect(screen.getByTestId("thread-id")).toHaveTextContent("thread-123");
    fireEvent.click(screen.getByTestId("new-thread-button"));
    expect(onNewThread).toHaveBeenCalledTimes(1);
  });
});
