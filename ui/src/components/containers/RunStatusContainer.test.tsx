import { render, screen } from "@testing-library/react";

import { RunStatusContainer } from "./RunStatusContainer";

describe("RunStatusContainer", () => {
  it("renders run status and per-tool progress rows", () => {
    render(
      <RunStatusContainer
        isRunning
        runningToolCount={2}
        toolProgressById={{
          "tool-1": { percent: 35, label: "Searching catalog" },
        }}
      />,
    );

    expect(screen.getByText("Working...")).toBeInTheDocument();
    expect(screen.getByText("2 tools running")).toBeInTheDocument();
    expect(screen.getByText("Searching catalog: 35%")).toBeInTheDocument();
  });
});
