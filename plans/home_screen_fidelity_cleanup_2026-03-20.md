# Home Screen Fidelity Cleanup

Date: 2026-03-20

## Scope

- Touched routes:
  - `/`
- Deferred routes:
  - `/agents`
  - `/agents/[agent]`
  - consultation chat behavior on live agent pages

## References

- `spec/uxuimarch20/tasklist.md`
- `spec/uxuimarch20/screenshots/home_screen_columns_not_aligned.png`
- `design_references/stitch_design/screen.png`
- `design_references/stitch_design/DESIGN.md`

## Current validated regressions

- Home navigation still uses `My Designs` plus `Workspaces` instead of the target `My Designs`, `Gallery`, and `History`.
- Home header chrome still uses the rollout-era workspace grid launcher instead of the thinner notification, settings, and profile treatment.
- The left context rail still uses the generic rounded-pill active state from the shared editorial primitives rather than the flat full-width strip from the target.
- Home cards still depend on backend ordering, use staggered widths/transforms, and keep the headline inside a white image overlay instead of presenting the main copy below the image.
- The right consultation rail still shows the generic `AI` badge and `Chat` `New` pill treatment instead of the simpler white rail list in the reference.

## Non-issues validated during repro

- The `CopilotKit v1.50` banner and floating diamond seen in the user-provided screenshot do not appear in a clean headless browser run against the app. They appear to come from the browser session, not from repo code.
- `The Archives` and `Update Brief` are already present on the current home page; this pass only needs to tighten their fidelity.

## States to verify

- Loading: home skeleton and loading launcher state.
- Success: loaded home page at canonical desktop width.
- Error: agent fetch fallback message still renders.
- Stress: home remains coherent at a narrower desktop width where the three-column composition compresses.

## Acceptance checks

- Home nav labels and right-side icons match the Stitch reference closely enough to remove the rollout-era launcher chrome.
- Card order is deterministic and matches the intended editorial sequence.
- Home cards align without the current staggered composition drift.
- Left and right rails read as the lighter Stitch home composition without breaking the shared agent-page shell.
- Focused tests cover the home nav labels and the deterministic card order/composition.
