export type Room3DSnapshotCreateRequest = {
  snapshot_asset_id: string;
  room_3d_asset_id: string | null;
  camera: {
    position_m: [number, number, number];
    target_m: [number, number, number];
    fov_deg: number;
  };
  lighting: {
    light_fixture_ids: string[];
    emphasized_light_count: number;
  };
  comment: string | null;
  run_id: string | null;
};

export type Room3DSnapshotResponse = {
  room_3d_snapshot_id: string;
  thread_id: string;
  run_id: string | null;
  snapshot_asset_id: string;
  room_3d_asset_id: string | null;
  camera: {
    position_m: [number, number, number];
    target_m: [number, number, number];
    fov_deg: number;
  };
  lighting: {
    light_fixture_ids: string[];
    emphasized_light_count: number;
  };
  comment: string | null;
  created_at: string;
};

export async function createRoom3DSnapshot(
  threadId: string,
  payload: Room3DSnapshotCreateRequest,
): Promise<Room3DSnapshotResponse> {
  const response = await fetch("/api/room-3d/snapshots", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-thread-id": threadId,
      ...(payload.run_id ? { "x-run-id": payload.run_id } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Room 3D snapshot request failed with status ${response.status}`);
  }
  return (await response.json()) as Room3DSnapshotResponse;
}
