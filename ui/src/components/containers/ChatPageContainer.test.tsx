import { render, screen } from "@testing-library/react";

import { ChatPageContainer } from "./ChatPageContainer";

describe("ChatPageContainer", () => {
  it("renders the top-level chat container shell", () => {
    render(<ChatPageContainer />);

    expect(
      screen.getByRole("heading", { name: "CopilotKit UI" }),
    ).toBeInTheDocument();
  });
});
