import { render } from "@testing-library/react";
import { vi } from "vitest";

import { CopilotToolRenderers } from "./CopilotToolRenderers";

const {
  useDefaultToolRendererMock,
  useCatalogToolRenderersMock,
  useImageAnalysisToolRenderersMock,
} = vi.hoisted(() => ({
  useDefaultToolRendererMock: vi.fn(),
  useCatalogToolRenderersMock: vi.fn(),
  useImageAnalysisToolRenderersMock: vi.fn(),
}));

vi.mock("@/components/copilotkit/renderers/useDefaultToolRenderer", () => ({
  useDefaultToolRenderer: useDefaultToolRendererMock,
}));

vi.mock("@/components/copilotkit/renderers/useCatalogToolRenderers", () => ({
  useCatalogToolRenderers: useCatalogToolRenderersMock,
}));

vi.mock("@/components/copilotkit/renderers/useImageAnalysisToolRenderers", () => ({
  useImageAnalysisToolRenderers: useImageAnalysisToolRenderersMock,
}));

describe("CopilotToolRenderers", () => {
  beforeEach(() => {
    useDefaultToolRendererMock.mockReset();
    useCatalogToolRenderersMock.mockReset();
    useImageAnalysisToolRenderersMock.mockReset();
  });

  it("forwards optional catalog callbacks and thread context to renderer hooks", () => {
    const onBundleSelected = vi.fn();
    const onBundleProposed = vi.fn();
    const onFloorPlanRendered = vi.fn();

    render(
      <CopilotToolRenderers
        onBundleSelected={onBundleSelected}
        onBundleProposed={onBundleProposed}
        onFloorPlanRendered={onFloorPlanRendered}
        roomId="room-456"
        threadId="thread-123"
      />,
    );

    expect(useDefaultToolRendererMock).toHaveBeenCalledTimes(1);
    expect(useCatalogToolRenderersMock).toHaveBeenCalledWith({
      onBundleSelected,
      onBundleProposed,
      onFloorPlanRendered,
    });
    expect(useImageAnalysisToolRenderersMock).toHaveBeenCalledWith({
      roomId: "room-456",
      threadId: "thread-123",
    });
  });

  it("omits unset optional props instead of passing undefined callbacks", () => {
    render(<CopilotToolRenderers />);

    expect(useCatalogToolRenderersMock).toHaveBeenCalledWith({});
    expect(useImageAnalysisToolRenderersMock).toHaveBeenCalledWith({});
  });
});
