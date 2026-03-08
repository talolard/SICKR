"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { forwardRef, useImperativeHandle, useMemo, useRef } from "react";
import type { MutableRefObject, ReactElement } from "react";
import {
  CanvasTexture,
  RepeatWrapping,
  SRGBColorSpace,
  type PerspectiveCamera,
  type Texture,
  type WebGLRenderer,
} from "three";

import type { FloorPlanScene } from "@/lib/floorPlanScene";

type FloorPlanScene3DProps = {
  scene: FloorPlanScene;
};

export type FloorPlanScene3DSnapshot = {
  captured_at: string;
  image_data_url: string;
  camera: {
    position_m: [number, number, number];
    target_m: [number, number, number];
    fov_deg: number;
  };
  lighting: {
    light_fixture_ids: string[];
    emphasized_light_count: number;
  };
};

export type FloorPlanScene3DHandle = {
  capturePng: () => FloorPlanScene3DSnapshot;
  setInteriorView: () => void;
  resetOverview: () => void;
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
const DEFAULT_CAMERA_FOV_DEG = 50;

type InitialCameraSettings = {
  position: [number, number, number];
  target: [number, number, number];
  fovDeg: number;
};

type OrbitControlsHandle = {
  target: { set: (x: number, y: number, z: number) => void };
  update: () => void;
};

type SceneTextures = {
  floor: Texture | null;
  wall: Texture | null;
  wood: Texture | null;
};

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

function hashString(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function buildStripedTexture({
  baseHex,
  stripeHex,
  stripeEveryPx,
}: {
  baseHex: string;
  stripeHex: string;
  stripeEveryPx: number;
}): Texture | null {
  if (typeof document === "undefined") {
    return null;
  }
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }
  context.fillStyle = baseHex;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = stripeHex;
  for (let y = 0; y < canvas.height; y += stripeEveryPx) {
    context.fillRect(0, y, canvas.width, Math.max(1, Math.floor(stripeEveryPx / 5)));
  }
  const texture = new CanvasTexture(canvas);
  texture.wrapS = RepeatWrapping;
  texture.wrapT = RepeatWrapping;
  texture.repeat.set(4, 4);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

function createSceneTextures(): SceneTextures {
  return {
    floor: buildStripedTexture({
      baseHex: "#efeee9",
      stripeHex: "#e0ddd4",
      stripeEveryPx: 24,
    }),
    wall: buildStripedTexture({
      baseHex: "#d6d0c2",
      stripeHex: "#c8c1b3",
      stripeEveryPx: 32,
    }),
    wood: buildStripedTexture({
      baseHex: "#7b5b45",
      stripeHex: "#6a4a35",
      stripeEveryPx: 18,
    }),
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

function RoomScene({ geometry }: { geometry: SceneGeometry }): ReactElement {
  const lightFixtures = geometry.fixtures.filter((fixture) => fixture.kind === "light");
  const socketFixtures = geometry.fixtures.filter((fixture) => fixture.kind === "socket");
  const textures = useMemo(createSceneTextures, []);

  return (
    <>
      <ambientLight intensity={0.65} />
      <directionalLight intensity={0.45} position={[2.5, 3, 2.5]} />
      <pointLight
        intensity={0.25}
        position={[
          geometry.roomLengthM * 0.5,
          geometry.roomHeightM,
          geometry.roomDepthM * 0.5,
        ]}
      />

      <mesh
        position={[geometry.roomLengthM * 0.5, 0, geometry.roomDepthM * 0.5]}
        receiveShadow
      >
        <boxGeometry args={[geometry.roomLengthM, 0.02, geometry.roomDepthM]} />
        <meshStandardMaterial
          color="#ece9e1"
          map={textures.floor}
          metalness={0.04}
          roughness={0.9}
        />
      </mesh>

      {geometry.walls.map((wall) => (
        <mesh key={wall.id} position={wall.center} rotation={[0, -wall.angleRad, 0]}>
          <boxGeometry args={[wall.lengthM, wall.heightM, wall.thicknessM]} />
          <meshStandardMaterial
            color="#d9d2c3"
            map={textures.wall}
            metalness={0.03}
            roughness={0.95}
          />
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
          <meshStandardMaterial
            color="#94caff"
            emissive="#15364e"
            transparent
            opacity={0.55}
          />
        </mesh>
      ))}

      {geometry.placements.map((placement) => (
        <mesh key={placement.id} position={placement.center}>
          <boxGeometry args={placement.size} />
          <meshStandardMaterial
            color={
              placement.color ??
              ["#80614f", "#5e7a89", "#6f7e64", "#8b6f5a"][hashString(placement.id) % 4]
            }
            map={textures.wood}
            roughness={0.65}
            metalness={0.08}
          />
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
            <meshStandardMaterial
              color="#fbbf24"
              emissive="#f59e0b"
              emissiveIntensity={1.7}
            />
          </mesh>
          <pointLight
            color="#ffd37a"
            intensity={0.65}
            distance={3}
            position={[
              fixture.position[0],
              fixture.position[1] + 0.05,
              fixture.position[2],
            ]}
          />
        </group>
      ))}
    </>
  );
}

function CaptureBridge({
  glRef,
  cameraRef,
}: {
  glRef: MutableRefObject<WebGLRenderer | null>;
  cameraRef: MutableRefObject<PerspectiveCamera | null>;
}): null {
  const { gl, camera } = useThree();
  glRef.current = gl;
  cameraRef.current = camera as PerspectiveCamera;
  return null;
}

export const FloorPlanScene3D = forwardRef<FloorPlanScene3DHandle, FloorPlanScene3DProps>(
  function FloorPlanScene3D({ scene }: FloorPlanScene3DProps, ref): ReactElement {
    const geometry = useMemo(() => toSceneGeometry(scene), [scene]);
    const initialCamera = useMemo(
      () => computeInitialCameraSettings(geometry),
      [geometry],
    );
    const hasWebGl =
      typeof window !== "undefined" && "WebGLRenderingContext" in window;
    const glRef = useRef<WebGLRenderer | null>(null);
    const cameraRef = useRef<PerspectiveCamera | null>(null);
    const controlsRef = useRef<OrbitControlsHandle | null>(null);
    const lightFixtureIds = useMemo(
      () =>
        (scene.fixtures ?? [])
          .filter((fixture) => fixture.fixture_kind === "light")
          .map((fixture) => fixture.fixture_id),
      [scene.fixtures],
    );

    useImperativeHandle(ref, () => ({
      capturePng: (): FloorPlanScene3DSnapshot => {
        const renderer = glRef.current;
        const camera = cameraRef.current;
        if (!renderer || !camera) {
          throw new Error("3D renderer is not ready yet.");
        }
        return {
          captured_at: new Date().toISOString(),
          image_data_url: renderer.domElement.toDataURL("image/png"),
          camera: {
            position_m: [
              Number(camera.position.x.toFixed(3)),
              Number(camera.position.y.toFixed(3)),
              Number(camera.position.z.toFixed(3)),
            ],
            target_m: [
              Number((geometry.roomLengthM * 0.5).toFixed(3)),
              Number((geometry.roomHeightM * 0.5).toFixed(3)),
              Number((geometry.roomDepthM * 0.5).toFixed(3)),
            ],
            fov_deg: Number(camera.fov.toFixed(2)),
          },
          lighting: {
            light_fixture_ids: lightFixtureIds,
            emphasized_light_count: lightFixtureIds.length,
          },
        };
      },
      setInteriorView: (): void => {
        const camera = cameraRef.current;
        const controls = controlsRef.current;
        if (!camera || !controls) {
          return;
        }
        const centerX = geometry.roomLengthM * 0.5;
        const centerZ = geometry.roomDepthM * 0.5;
        camera.position.set(centerX, Math.max(1.45, geometry.roomHeightM * 0.58), centerZ - 0.2);
        controls.target.set(centerX, Math.max(1.2, geometry.roomHeightM * 0.45), centerZ);
        controls.update();
      },
      resetOverview: (): void => {
        const camera = cameraRef.current;
        const controls = controlsRef.current;
        if (!camera || !controls) {
          return;
        }
        camera.position.set(...initialCamera.position);
        controls.target.set(...initialCamera.target);
        controls.update();
      },
    }));

    if (!hasWebGl) {
      return (
        <div className="rounded border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700">
          3D preview unavailable in this environment.
        </div>
      );
    }

    return (
      <div
        className="h-[420px] w-full rounded border border-gray-200 bg-[#e8edf2]"
        data-testid="floor-plan-3d-canvas"
      >
        <Canvas
          camera={{
            position: initialCamera.position,
            fov: initialCamera.fovDeg,
            near: 0.01,
            far: 1500,
          }}
        >
          <CaptureBridge cameraRef={cameraRef} glRef={glRef} />
          <RoomScene geometry={geometry} />
          <OrbitControls
            ref={controlsRef}
            enableDamping
            enablePan
            makeDefault
            maxDistance={28}
            maxPolarAngle={Math.PI * 0.495}
            minDistance={0.16}
            minPolarAngle={Math.PI * 0.05}
            panSpeed={0.85}
            target={initialCamera.target}
            zoomSpeed={1.25}
          />
        </Canvas>
      </div>
    );
  },
);
