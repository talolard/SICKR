import type { FloorPlanScene } from "@/lib/floorPlanScene";

const CM_TO_M = 0.01;
const GEOMETRY_EPSILON_M = 1e-4;
const DEFAULT_CAMERA_FOV_DEG = 50;
const DEFAULT_DOOR_HEIGHT_RATIO = 0.82;
const DEFAULT_DOOR_MAX_HEIGHT_M = 2.1;

type OpeningKind = "door" | "window";

export type OpeningHole3D = {
  openingId: string;
  kind: OpeningKind;
  alongStartM: number;
  alongEndM: number;
  zMinM: number;
  zMaxM: number;
};

export type Wall3D = {
  id: string;
  start: [number, number, number];
  center: [number, number, number];
  lengthM: number;
  angleRad: number;
  thicknessM: number;
  heightM: number;
  openings: OpeningHole3D[];
};

export type OpeningInsert3D = {
  id: string;
  kind: OpeningKind;
  center: [number, number, number];
  lengthM: number;
  angleRad: number;
  thicknessM: number;
  heightM: number;
};

type Placement3D = {
  id: string;
  center: [number, number, number];
  size: [number, number, number];
  color: string;
};

type Fixture3D = {
  id: string;
  kind: "socket" | "light";
  position: [number, number, number];
};

export type SceneGeometry = {
  roomLengthM: number;
  roomDepthM: number;
  roomHeightM: number;
  walls: Wall3D[];
  openingInserts: OpeningInsert3D[];
  placements: Placement3D[];
  fixtures: Fixture3D[];
};

export type InitialCameraSettings = {
  position: [number, number, number];
  target: [number, number, number];
  fovDeg: number;
};

type WallFrame = {
  wall: Wall3D;
  startX: number;
  startZ: number;
  unitX: number;
  unitZ: number;
};

type DoorOpening = NonNullable<FloorPlanScene["architecture"]["doors"]>[number];
type WindowOpening = NonNullable<FloorPlanScene["architecture"]["windows"]>[number];

type OpeningRect = {
  openingId: string;
  kind: OpeningKind;
  alongStartM: number;
  alongEndM: number;
  zMinM: number;
  zMaxM: number;
  centerX: number;
  centerZ: number;
  angleRad: number;
};

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function projectAlong(pointX: number, pointZ: number, frame: WallFrame): number {
  return (pointX - frame.startX) * frame.unitX + (pointZ - frame.startZ) * frame.unitZ;
}

function projectPerpendicular(pointX: number, pointZ: number, frame: WallFrame): number {
  // Right-handed orthogonal unit to wall direction.
  const perpX = -frame.unitZ;
  const perpZ = frame.unitX;
  return (pointX - frame.startX) * perpX + (pointZ - frame.startZ) * perpZ;
}

function overlapOnAxis(
  firstStart: number,
  firstEnd: number,
  secondStart: number,
  secondEnd: number,
): boolean {
  return firstStart < secondEnd - GEOMETRY_EPSILON_M && secondStart < firstEnd - GEOMETRY_EPSILON_M;
}

function overlapsExisting(candidate: OpeningRect, existing: OpeningRect[]): boolean {
  return existing.some((item) => {
    const overlapAlong = overlapOnAxis(
      candidate.alongStartM,
      candidate.alongEndM,
      item.alongStartM,
      item.alongEndM,
    );
    const overlapHeight = overlapOnAxis(candidate.zMinM, candidate.zMaxM, item.zMinM, item.zMaxM);
    return overlapAlong && overlapHeight;
  });
}

function inferDoorVerticalRangeM(door: DoorOpening, roomHeightM: number): {
  zMinM: number;
  zMaxM: number;
} {
  const zMinFromScene = door.z_min_cm == null ? 0 : door.z_min_cm * CM_TO_M;
  const defaultMaxM = Math.min(DEFAULT_DOOR_MAX_HEIGHT_M, roomHeightM * DEFAULT_DOOR_HEIGHT_RATIO);
  const zMaxFromScene = door.z_max_cm == null ? defaultMaxM : door.z_max_cm * CM_TO_M;
  const zMinM = clamp(zMinFromScene, 0, roomHeightM);
  const zMaxM = clamp(zMaxFromScene, zMinM + GEOMETRY_EPSILON_M, roomHeightM);
  return { zMinM, zMaxM };
}

function inferWindowVerticalRangeM(
  windowOpening: WindowOpening,
  roomHeightM: number,
): { zMinM: number; zMaxM: number } {
  const defaultMinM = roomHeightM * 0.45;
  const defaultMaxM = roomHeightM * 0.78;
  const zMinRawM = windowOpening.z_min_cm == null ? defaultMinM : windowOpening.z_min_cm * CM_TO_M;
  const zMaxRawM = windowOpening.z_max_cm == null ? defaultMaxM : windowOpening.z_max_cm * CM_TO_M;
  const zMinM = clamp(zMinRawM, 0, roomHeightM);
  const zMaxM = clamp(zMaxRawM, zMinM + GEOMETRY_EPSILON_M, roomHeightM);
  return { zMinM, zMaxM };
}

function openingToRect(
  frame: WallFrame,
  opening: {
    opening_id: string;
    start_cm: { x_cm: number; y_cm: number };
    end_cm: { x_cm: number; y_cm: number };
  },
  kind: OpeningKind,
  zRange: { zMinM: number; zMaxM: number },
): OpeningRect | null {
  const startXM = opening.start_cm.x_cm * CM_TO_M;
  const startZM = opening.start_cm.y_cm * CM_TO_M;
  const endXM = opening.end_cm.x_cm * CM_TO_M;
  const endZM = opening.end_cm.y_cm * CM_TO_M;

  const startAlongM = projectAlong(startXM, startZM, frame);
  const endAlongM = projectAlong(endXM, endZM, frame);

  const alongMinM = clamp(
    Math.min(startAlongM, endAlongM),
    0,
    Math.max(frame.wall.lengthM - GEOMETRY_EPSILON_M, 0),
  );
  const alongMaxM = clamp(Math.max(startAlongM, endAlongM), alongMinM + GEOMETRY_EPSILON_M, frame.wall.lengthM);

  if (alongMaxM - alongMinM < GEOMETRY_EPSILON_M) {
    return null;
  }

  const startPerpM = Math.abs(projectPerpendicular(startXM, startZM, frame));
  const endPerpM = Math.abs(projectPerpendicular(endXM, endZM, frame));
  const wallToleranceM = Math.max(frame.wall.thicknessM * 0.6, 0.08);
  if (startPerpM > wallToleranceM || endPerpM > wallToleranceM) {
    return null;
  }

  return {
    openingId: opening.opening_id,
    kind,
    alongStartM: alongMinM,
    alongEndM: alongMaxM,
    zMinM: zRange.zMinM,
    zMaxM: zRange.zMaxM,
    centerX: frame.startX + frame.unitX * (alongMinM + alongMaxM) * 0.5,
    centerZ: frame.startZ + frame.unitZ * (alongMinM + alongMaxM) * 0.5,
    angleRad: frame.wall.angleRad,
  };
}

function buildWallFrames(scene: FloorPlanScene): WallFrame[] {
  const roomHeightM = scene.architecture.dimensions_cm.height_z_cm * CM_TO_M;
  return scene.architecture.walls.map((wall) => {
    const startX = wall.start_cm.x_cm * CM_TO_M;
    const startZ = wall.start_cm.y_cm * CM_TO_M;
    const endX = wall.end_cm.x_cm * CM_TO_M;
    const endZ = wall.end_cm.y_cm * CM_TO_M;
    const dx = endX - startX;
    const dz = endZ - startZ;
    const lengthM = Math.max(GEOMETRY_EPSILON_M, Math.hypot(dx, dz));
    const unitX = dx / lengthM;
    const unitZ = dz / lengthM;
    const angleRad = Math.atan2(dz, dx);
    const thicknessM = (wall.thickness_cm ?? 10) * CM_TO_M;

    const wallShape: Wall3D = {
      id: wall.wall_id,
      start: [startX, 0, startZ],
      center: [(startX + endX) * 0.5, roomHeightM * 0.5, (startZ + endZ) * 0.5],
      lengthM,
      angleRad,
      thicknessM,
      heightM: roomHeightM,
      openings: [],
    };

    return {
      wall: wallShape,
      startX,
      startZ,
      unitX,
      unitZ,
    };
  });
}

function locateOpeningFrame(
  frames: WallFrame[],
  opening: {
    start_cm: { x_cm: number; y_cm: number };
    end_cm: { x_cm: number; y_cm: number };
  },
): WallFrame | null {
  const startXM = opening.start_cm.x_cm * CM_TO_M;
  const startZM = opening.start_cm.y_cm * CM_TO_M;
  const endXM = opening.end_cm.x_cm * CM_TO_M;
  const endZM = opening.end_cm.y_cm * CM_TO_M;

  let bestFrame: WallFrame | null = null;
  let bestScore = Number.POSITIVE_INFINITY;

  for (const frame of frames) {
    const startAlongM = projectAlong(startXM, startZM, frame);
    const endAlongM = projectAlong(endXM, endZM, frame);
    const minAlongM = Math.min(startAlongM, endAlongM);
    const maxAlongM = Math.max(startAlongM, endAlongM);
    if (minAlongM < -0.1 || maxAlongM > frame.wall.lengthM + 0.1) {
      continue;
    }

    const startPerpM = Math.abs(projectPerpendicular(startXM, startZM, frame));
    const endPerpM = Math.abs(projectPerpendicular(endXM, endZM, frame));
    const score = startPerpM + endPerpM;
    if (score < bestScore) {
      bestScore = score;
      bestFrame = frame;
    }
  }

  return bestFrame;
}

function openingRectToInsert(rect: OpeningRect, wall: Wall3D): OpeningInsert3D {
  return {
    id: rect.openingId,
    kind: rect.kind,
    center: [rect.centerX, (rect.zMinM + rect.zMaxM) * 0.5, rect.centerZ],
    lengthM: rect.alongEndM - rect.alongStartM,
    angleRad: rect.angleRad,
    thicknessM: Math.max(0.03, wall.thicknessM * 0.25),
    heightM: rect.zMaxM - rect.zMinM,
  };
}

export function toSceneGeometry(scene: FloorPlanScene): SceneGeometry {
  const dims = scene.architecture.dimensions_cm;
  const roomLengthM = dims.length_x_cm * CM_TO_M;
  const roomDepthM = dims.depth_y_cm * CM_TO_M;
  const roomHeightM = dims.height_z_cm * CM_TO_M;

  const frames = buildWallFrames(scene);
  const openingInserts: OpeningInsert3D[] = [];

  const byWallId = new Map<string, OpeningRect[]>();

  for (const door of scene.architecture.doors ?? []) {
    const frame = locateOpeningFrame(frames, door);
    if (!frame) {
      continue;
    }
    const zRange = inferDoorVerticalRangeM(door, roomHeightM);
    const rect = openingToRect(frame, door, "door", zRange);
    if (!rect) {
      continue;
    }
    const existing = byWallId.get(frame.wall.id) ?? [];
    if (overlapsExisting(rect, existing)) {
      continue;
    }
    existing.push(rect);
    byWallId.set(frame.wall.id, existing);
  }

  for (const windowOpening of scene.architecture.windows ?? []) {
    const frame = locateOpeningFrame(frames, windowOpening);
    if (!frame) {
      continue;
    }
    const zRange = inferWindowVerticalRangeM(windowOpening, roomHeightM);
    const rect = openingToRect(frame, windowOpening, "window", zRange);
    if (!rect) {
      continue;
    }
    const existing = byWallId.get(frame.wall.id) ?? [];
    if (overlapsExisting(rect, existing)) {
      continue;
    }
    existing.push(rect);
    byWallId.set(frame.wall.id, existing);
  }

  const walls: Wall3D[] = frames.map((frame) => {
    const openingRects = [...(byWallId.get(frame.wall.id) ?? [])].sort((left, right) => {
      if (left.alongStartM !== right.alongStartM) {
        return left.alongStartM - right.alongStartM;
      }
      return left.zMinM - right.zMinM;
    });
    for (const rect of openingRects) {
      openingInserts.push(openingRectToInsert(rect, frame.wall));
    }

    return {
      ...frame.wall,
      openings: openingRects.map((rect) => ({
        openingId: rect.openingId,
        kind: rect.kind,
        alongStartM: rect.alongStartM,
        alongEndM: rect.alongEndM,
        zMinM: rect.zMinM,
        zMaxM: rect.zMaxM,
      })),
    };
  });

  const placements: Placement3D[] = (scene.placements ?? []).map((placement) => ({
    id: placement.placement_id,
    center: [
      (placement.position_cm.x_cm + placement.size_cm.x_cm * 0.5) * CM_TO_M,
      ((placement.z_cm ?? 0) + placement.size_cm.z_cm * 0.5) * CM_TO_M,
      (placement.position_cm.y_cm + placement.size_cm.y_cm * 0.5) * CM_TO_M,
    ],
    size: [
      placement.size_cm.x_cm * CM_TO_M,
      placement.size_cm.z_cm * CM_TO_M,
      placement.size_cm.y_cm * CM_TO_M,
    ],
    color: placement.color ?? "#7c5f4b",
  }));

  const fixtures: Fixture3D[] = (scene.fixtures ?? []).map((fixture) => ({
    id: fixture.fixture_id,
    kind: fixture.fixture_kind,
    position: [fixture.x_cm * CM_TO_M, (fixture.z_cm ?? 0) * CM_TO_M, fixture.y_cm * CM_TO_M],
  }));

  return {
    roomLengthM,
    roomDepthM,
    roomHeightM,
    walls,
    openingInserts,
    placements,
    fixtures,
  };
}

export function computeInitialCameraSettings(
  geometry: Pick<SceneGeometry, "roomLengthM" | "roomDepthM" | "roomHeightM">,
): InitialCameraSettings {
  const maxPlanSpanM = Math.max(geometry.roomLengthM, geometry.roomDepthM, 0.1);
  const centerX = geometry.roomLengthM * 0.5;
  const centerZ = geometry.roomDepthM * 0.5;
  const topDownHeightM = Math.max(geometry.roomHeightM * 2.6, maxPlanSpanM * 1.45);
  const depthOffsetM = maxPlanSpanM * 0.24;
  return {
    position: [centerX, topDownHeightM, centerZ + depthOffsetM],
    target: [centerX, geometry.roomHeightM * 0.22, centerZ],
    fovDeg: DEFAULT_CAMERA_FOV_DEG,
  };
}
