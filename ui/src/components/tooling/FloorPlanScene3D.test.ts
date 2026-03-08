import { computeInitialCameraSettings } from "./FloorPlanScene3D";

describe("computeInitialCameraSettings", () => {
  it("frames room from a readable elevated perspective", () => {
    const camera = computeInitialCameraSettings({
      roomLengthM: 4.2,
      roomDepthM: 3.2,
      roomHeightM: 2.6,
    });

    expect(camera.position[0]).toBeCloseTo(2.1, 3);
    expect(camera.position[1]).toBeGreaterThan(4.5);
    expect(camera.position[2]).toBeGreaterThan(1.6);
    expect(camera.target[0]).toBeCloseTo(2.1, 3);
    expect(camera.target[2]).toBeCloseTo(1.6, 3);
    expect(camera.fovDeg).toBe(50);
  });

  it("scales camera height with larger room footprints", () => {
    const small = computeInitialCameraSettings({
      roomLengthM: 3,
      roomDepthM: 2.5,
      roomHeightM: 2.4,
    });
    const large = computeInitialCameraSettings({
      roomLengthM: 8,
      roomDepthM: 6,
      roomHeightM: 3,
    });

    expect(large.position[1]).toBeGreaterThan(small.position[1]);
    expect(large.position[2]).toBeGreaterThan(small.position[2]);
  });
});
