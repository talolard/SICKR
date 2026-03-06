# React Three Fiber + Three.js Notes

Sources reviewed:
- Context7 `/pmndrs/react-three-fiber` docs for Canvas scene setup and light/mesh primitives.
- Context7 `/mrdoob/three.js` docs for line/segment geometry patterns with `BufferGeometry`.

Key takeaways used in this repo:
- `Canvas` from `@react-three/fiber` is the primary render root for declarative Three scenes.
- Basic room visualization can be built with standard primitives:
  - `ambientLight`, `directionalLight`, `pointLight`
  - `mesh` + `boxGeometry` + `meshStandardMaterial`
- For user inspection, `OrbitControls` from `@react-three/drei` provides straightforward camera interaction.
- For wall/opening overlays, Three.js line/segment approaches are available via `BufferGeometry.setFromPoints(...)` and `Line/LineSegments`.

Implementation guidance:
- Keep world units consistent (convert centimeters to meters once).
- Keep mesh IDs stable (wall/placement/fixture IDs) so rerenders remain deterministic.
- Prefer simple meshes over complex boolean geometry for initial UI reliability.
