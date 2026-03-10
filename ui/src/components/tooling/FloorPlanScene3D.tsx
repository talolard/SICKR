"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { forwardRef, useImperativeHandle, useMemo, useRef } from "react";
import type { ElementRef, MutableRefObject, ReactElement } from "react";
import {
  CanvasTexture,
  ExtrudeGeometry,
  Path,
  RepeatWrapping,
  SRGBColorSpace,
  Shape,
  type PerspectiveCamera,
  type Texture,
  type WebGLRenderer,
} from "three";

import type { FloorPlanScene } from "@/lib/floorPlanScene";
import {
  computeInitialCameraSettings,
  toSceneGeometry,
  type SceneGeometry,
  type Wall3D,
} from "@/lib/floorPlanScene3dGeometry";

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

type SceneTextures = {
  floor: Texture | null;
  wall: Texture | null;
  wood: Texture | null;
};

type OrbitControlsHandle = ElementRef<typeof OrbitControls>;

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

function buildWallGeometry(wall: Wall3D): ExtrudeGeometry {
  const shape = new Shape();
  shape.moveTo(0, 0);
  shape.lineTo(wall.lengthM, 0);
  shape.lineTo(wall.lengthM, wall.heightM);
  shape.lineTo(0, wall.heightM);
  shape.lineTo(0, 0);

  for (const opening of wall.openings) {
    const hole = new Path();
    hole.moveTo(opening.alongStartM, opening.zMinM);
    hole.lineTo(opening.alongEndM, opening.zMinM);
    hole.lineTo(opening.alongEndM, opening.zMaxM);
    hole.lineTo(opening.alongStartM, opening.zMaxM);
    hole.lineTo(opening.alongStartM, opening.zMinM);
    shape.holes.push(hole);
  }

  const geometry = new ExtrudeGeometry(shape, {
    depth: wall.thicknessM,
    bevelEnabled: false,
  });
  // Center the extrusion on wall centerline so placement aligns with opening inserts.
  geometry.translate(0, 0, -wall.thicknessM * 0.5);
  return geometry;
}

function WallWithOpenings({ wall, wallTexture }: { wall: Wall3D; wallTexture: Texture | null }): ReactElement {
  const wallGeometry = useMemo(() => buildWallGeometry(wall), [wall]);

  return (
    <mesh
      geometry={wallGeometry}
      position={wall.start}
      rotation={[0, -wall.angleRad, 0]}
    >
      <meshStandardMaterial
        color="#d9d2c3"
        map={wallTexture}
        metalness={0.03}
        roughness={0.95}
      />
    </mesh>
  );
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
        <WallWithOpenings key={wall.id} wall={wall} wallTexture={textures.wall} />
      ))}

      {geometry.openingInserts.map((opening) => (
        <mesh key={opening.id} position={opening.center} rotation={[0, -opening.angleRad, 0]}>
          <boxGeometry args={[opening.lengthM, opening.heightM, opening.thicknessM]} />
          {opening.kind === "door" ? (
            <meshStandardMaterial color="#8b6b54" map={textures.wood} roughness={0.72} metalness={0.06} />
          ) : (
            <meshStandardMaterial
              color="#94caff"
              emissive="#15364e"
              transparent
              opacity={0.48}
              depthWrite={false}
            />
          )}
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
