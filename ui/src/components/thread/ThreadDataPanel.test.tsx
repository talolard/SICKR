import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { ThreadDataPanel } from "./ThreadDataPanel";

vi.mock("@/lib/api/threadDataClient", () => ({
  getRoomThreadDetail: vi.fn(async () => ({
    thread_id: "thread-1",
    title: "Floor-plan hallway",
    room_id: "room-1",
    room_title: "Hallway",
    room_type: "hallway",
    status: "active",
    last_activity_at: null,
    run_count: 1,
    asset_count: 2,
    floor_plan_revision_count: 1,
    analysis_count: 0,
    search_count: 0,
  })),
  listRoomThreadAssets: vi.fn(async () => [
    {
      asset_id: "asset-png",
      uri: "/attachments/asset-png",
      run_id: "run-1",
      created_by_tool: "render_floor_plan",
      kind: "floor_plan_png",
      display_label: "Floor plan revision 2 (PNG preview)",
      mime_type: "image/png",
      file_name: "floor-plan.png",
      size_bytes: 1234,
      created_at: "2026-03-18T16:55:00Z",
    },
    {
      asset_id: "asset-svg",
      uri: "/attachments/asset-svg",
      run_id: "run-1",
      created_by_tool: "render_floor_plan",
      kind: "floor_plan_svg",
      display_label: "Floor plan revision 2 (SVG)",
      mime_type: "image/svg+xml",
      file_name: "floor-plan.svg",
      size_bytes: 1235,
      created_at: "2026-03-18T16:55:00Z",
    },
  ]),
  ThreadDataRequestError: class ThreadDataRequestError extends Error {
    status: number;

    constructor(status: number) {
      super(`status ${status}`);
      this.status = status;
    }
  },
}));

describe("ThreadDataPanel", () => {
  it("shows asset display labels instead of raw filenames", async () => {
    render(<ThreadDataPanel roomId="room-1" threadId="thread-1" />);

    await waitFor(() => {
      expect(screen.getByText("Latest assets")).toBeInTheDocument();
    });

    expect(screen.getByText("Floor plan revision 2 (PNG preview)")).toBeInTheDocument();
    expect(screen.getByText("Floor plan revision 2 (SVG)")).toBeInTheDocument();
    expect(screen.queryByText(/floor-plan\\.png/i)).not.toBeInTheDocument();
  });
});
