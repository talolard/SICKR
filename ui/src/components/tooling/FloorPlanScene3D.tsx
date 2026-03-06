"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useMemo } from "react";
import type { ReactElement } from "react";

import type { FloorPlanScene } from "@/lib/floorPlanScene";

type FloorPlanScene3DProps = {
  scene: FloorPlanScene;
};

type Segment3D = {
  id: string;
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

type SceneGeometry = {
  roomLengthM: number;
  roomDepthM: number;
  roomHeightM: number;
  walls: Segment3D[];
  doors: Segment3D[];
  windows: Segment3D[];
  placements: Placement3D[];
  fixtures: Fixture3D[];
};

const CM_TO_M = 0.01;

function toSceneGeometry(scene: FloorPlanScene): SceneGeometry {
  const dims = scene.architecture.dimensions_cm;
  const roomLengthM = dims.length_x_cm * CM_TO_M;
  const roomDepthM = dims.depth_y_cm * CM_TO_M;
  const roomHeightM = dims.height_z_cm * CM_TO_M;

  const walls: Segment3D[] = scene.architecture.walls.map((wall) => {
    const dxM = (wall.end_cm.x_cm - wall.start_cm.x_cm) * CM_TO_M;
    const dyM = (wall.end_cm.y_cm - wall.start_cm.y_cm) * CM_TO_M;
    const lengthM = Math.max(0.001, Math.hypot(dxM, dyM));
    return {
      id: wall.wall_id,
      center: [
        (wall.start_cm.x_cm + wall.end_cm.x_cm) * 0.5 * CM_TO_M,
        roomHeightM * 0.5,
        (wall.start_cm.y_cm + wall.end_cm.y_cm) * 0.5 * CM_TO_M,
      ],
      lengthM,
      angleRad: Math.atan2(dyM, dxM),
      thicknessM: (wall.thickness_cm ?? 10) * CM_TO_M,
      heightM: roomHeightM,
    };
  });

  const doors: Segment3D[] = (scene.architecture.doors ?? []).map((door) => {
    const dxM = (door.end_cm.x_cm - door.start_cm.x_cm) * CM_TO_M;
    const dyM = (door.end_cm.y_cm - door.start_cm.y_cm) * CM_TO_M;
    const lengthM = Math.max(0.001, Math.hypot(dxM, dyM));
    return {
      id: door.opening_id,
      center: [
        (door.start_cm.x_cm + door.end_cm.x_cm) * 0.5 * CM_TO_M,
        Math.min(1.05, roomHeightM * 0.4),
        (door.start_cm.y_cm + door.end_cm.y_cm) * 0.5 * CM_TO_M,
      ],
      lengthM,
      angleRad: Math.atan2(dyM, dxM),
      thicknessM: 0.03,
      heightM: Math.min(2.1, roomHeightM * 0.8),
    };
  });

  const windows: Segment3D[] = (scene.architecture.windows ?? []).map((window) => {
    const dxM = (window.end_cm.x_cm - window.start_cm.x_cm) * CM_TO_M;
    const dyM = (window.end_cm.y_cm - window.start_cm.y_cm) * CM_TO_M;
    const lengthM = Math.max(0.001, Math.hypot(dxM, dyM));
    const zMinM = (window.z_min_cm ?? dims.height_z_cm * 0.45) * CM_TO_M;
    const zMaxM = (window.z_max_cm ?? dims.height_z_cm * 0.78) * CM_TO_M;
    const heightM = Math.max(0.2, zMaxM - zMinM);
    return {
      id: window.opening_id,
      center: [
        (window.start_cm.x_cm + window.end_cm.x_cm) * 0.5 * CM_TO_M,
        zMinM + heightM * 0.5,
        (window.start_cm.y_cm + window.end_cm.y_cm) * 0.5 * CM_TO_M,
      ],
      lengthM,
      angleRad: Math.atan2(dyM, dxM),
      thicknessM: 0.03,
      heightM,
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
    position: [
      fixture.x_cm * CM_TO_M,
      (fixture.z_cm ?? 0) * CM_TO_M,
      fixture.y_cm * CM_TO_M,
    ],
  }));

  return {
    roomLengthM,
    roomDepthM,
    roomHeightM,
    walls,
    doors,
    windows,
    placements,
    fixtures,
  };
}

function RoomScene({ geometry }: { geometry: SceneGeometry }): ReactElement {
  const lightFixtures = geometry.fixtures.filter((fixture) => fixture.kind === "light");
  const socketFixtures = geometry.fixtures.filter((fixture) => fixture.kind === "socket");

  return (
    <>
      <ambientLight intensity={0.65} />
      <directionalLight intensity={0.45} position={[2.5, 3, 2.5]} />
      <pointLight intensity={0.25} position={[geometry.roomLengthM * 0.5, geometry.roomHeightM, geometry.roomDepthM * 0.5]} />

      <mesh position={[geometry.roomLengthM * 0.5, 0, geometry.roomDepthM * 0.5]} receiveShadow>
        <boxGeometry args={[geometry.roomLengthM, 0.02, geometry.roomDepthM]} />
        <meshStandardMaterial color="#ece9e1" />
      </mesh>

      {geometry.walls.map((wall) => (
        <mesh key={wall.id} position={wall.center} rotation={[0, -wall.angleRad, 0]}>
          <boxGeometry args={[wall.lengthM, wall.heightM, wall.thicknessM]} />
          <meshStandardMaterial color="#d9d2c3" />
        </mesh>
      ))}

      {geometry.doors.map((door) => (
        <mesh key={door.id} position={door.center} rotation={[0, -door.angleRad, 0]}>
          <boxGeometry args={[door.lengthM, door.heightM, door.thicknessM]} />
          <meshStandardMaterial color="#6ea8cc" transparent opacity={0.5} />
        </mesh>
      ))}

      {geometry.windows.map((window) => (
        <mesh key={window.id} position={window.center} rotation={[0, -window.angleRad, 0]}>
          <boxGeometry args={[window.lengthM, window.heightM, window.thicknessM]} />
          <meshStandardMaterial color="#94caff" emissive="#15364e" transparent opacity={0.55} />
        </mesh>
      ))}

      {geometry.placements.map((placement) => (
        <mesh key={placement.id} position={placement.center}>
          <boxGeometry args={placement.size} />
          <meshStandardMaterial color={placement.color} roughness={0.65} metalness={0.1} />
        </mesh>
      ))}

      {socketFixtures.map((fixture) => (
        <mesh key={fixture.id} position={fixture.position}>
          <sphereGeometry args={[0.05, 12, 12]} />
          <meshStandardMaterial color="#1f2937" />
        </mesh>
      ))}

      {lightFixtures.map((fixture) => (
        <group key={fixture.id}>
          <mesh position={fixture.position}>
            <sphereGeometry args={[0.07, 16, 16]} />
            <meshStandardMaterial color="#fbbf24" emissive="#f59e0b" emissiveIntensity={1.7} />
          </mesh>
          <pointLight
            color="#ffd37a"
            intensity={0.65}
            distance={3}
            position={[fixture.position[0], fixture.position[1] + 0.05, fixture.position[2]]}
          />
        </group>
      ))}

      <OrbitControls makeDefault />
    </>
  );
}

export function FloorPlanScene3D({ scene }: FloorPlanScene3DProps): ReactElement {
  const geometry = useMemo(() => toSceneGeometry(scene), [scene]);
  const hasWebGl = typeof window !== "undefined" && "WebGLRenderingContext" in window;

  if (!hasWebGl) {
    return (
      <div className="rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
        3D preview unavailable in this environment.
      </div>
    );
  }

  return (
    <div className="h-[420px] w-full rounded border border-gray-200 bg-[#e8edf2]" data-testid="floor-plan-3d-canvas">
      <Canvas camera={{ position: [geometry.roomLengthM * 0.5, geometry.roomHeightM * 0.85, geometry.roomDepthM * 1.25], fov: 55 }}>
        <RoomScene geometry={geometry} />
      </Canvas>
    </div>
  );
}
