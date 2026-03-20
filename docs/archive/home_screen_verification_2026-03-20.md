# Home Screen Verification 2026-03-20

## Scope

- Beads task: `tal_maria_ikea-19u.7`
- Home-coupled verification remainder for: `tal_maria_ikea-19u.8`
- Routes checked:
  - `/`
  - `/agents` through the shared `StudioShowcaseLayout` shell

## Visual References

- `design_references/stitch_design/home_screen/screen.png`
- `design_references/stitch_design/home_screen/code.html`
- `design_references/stitch_design/home_screen/DESIGN.md`
- `spec/uxui-march19/report.md`

## What This Pass Verifies

- Home rails read as aligned Stitch columns instead of floating editorial cards.
- Top-right home chrome stays on the lighter notification/settings/profile treatment.
- Launcher cards stay in the intended editorial order and keep the simplified below-image copy treatment.
- The home shell remains coherent at canonical desktop width and at a narrower desktop width where the right consultation rail drops away.
- Existing loading and agent-fetch fallback states remain covered by focused component tests.

## Automated Checks

- Focused component coverage:
  - `ui/src/components/agents/StudioShowcaseLayout.test.tsx`
  - `ui/src/components/navigation/AppNavBanner.test.tsx`
  - `ui/src/app/page.test.tsx`
- Mock real-page coverage:
  - `ui/e2e/mock-chat.spec.ts`
  - canonical desktop assertion for aligned left and right rails on `/`
  - narrower desktop assertion for coherent home layout when the right rail is hidden

## Local Validation Run

- `cd ui && pnpm test -- src/components/agents/StudioShowcaseLayout.test.tsx src/components/navigation/AppNavBanner.test.tsx src/app/page.test.tsx`
- `cd ui && pnpm playwright test e2e/mock-chat.spec.ts`
- `cd ui && pnpm typecheck`
- `make tidy`

## Human Review Notes

- Compare `/` against `design_references/stitch_design/home_screen/screen.png` at a 1440px desktop viewport.
- Confirm the left context rail begins immediately under the glass nav and the right consultation rail starts at the same vertical anchor.
- Confirm the launcher cards and archives section still read as one centered editorial column between those rails.
