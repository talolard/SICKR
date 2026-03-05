# UI Critique (Phase 2)

Context: review based on current UI screenshot and existing templates/CSS in:
- `src/ikea_agent/web/templates/web/base.html`
- `src/ikea_agent/web/templates/web/search.html`
- `src/ikea_agent/web/forms.py`

## Summary
The current page works functionally, but it behaves like an internal debug tool:
- filter UI is overloaded and hard to scan
- layout does not guide user intent
- results feel like log output, not product cards
- key quality-of-life controls are missing

The next UI pass should optimize for fast shopping workflows, not raw parameter exposure.

## Critical UX Problems

### 1) Filter form is a spreadsheet disguised as UI
Current behavior:
- 15+ flat inputs, little hierarchy
- exact/min/max triplicated for width/depth/height
- no basic vs advanced split

Impact:
- high cognitive load before first query
- users must parse API-like fields instead of being guided

Required changes:
- default visible: query, category, price range
- move dimensions and lower-frequency fields into collapsed `More filters`
- dimensions should be range-first; exact should be optional toggle mode

### 2) Labels and layout are visually expensive
Current behavior:
- labels and inputs rendered as separate grid nodes in template, so pairing is fragile
- repetitive label text (`Width min cm`, `Width max cm`, etc.)
- API-style copy (`min_price_eur`) leaks into UI tone

Required changes:
- grouped field component per control (`label + input` together)
- compact labels with unit adornments:
  - `Price: € min / € max`
  - `Width: min / max` with `cm` suffix
- consistent vertical rhythm and section spacing

### 3) Missing quality-of-life controls
Current behavior:
- no reset/clear filters
- no sort controls
- no active-filter summary

Required changes:
- add `Reset` action
- add sort dropdown: `Relevance`, `Price low-high`, `Price high-low`, `Size`
- show active filter chips under search controls

### 4) Results read like debug output
Current behavior:
- minimal hierarchy
- taxonomy slugs exposed directly
- raw semantic score shown inline (`semantic cosine score 0.723`)

Required changes:
- result card structure:
  - product name
  - price (prominent)
  - human-formatted dimensions/key facts
  - friendly category label (not raw slug path)
  - clear CTA(s)
- move score to optional `Why this result?` disclosure
- map score bands to user-facing confidence labels when needed

### 5) Shortlist interaction is noisy
Current behavior:
- per-result note input always visible

Required changes:
- make `Add to shortlist` primary action
- make notes optional after click (expand, modal, or drawer)

### 6) Accessibility/usability debt risk
Likely issues in this dense form pattern:
- weak focus visibility
- keyboard traversal friction
- low consistency for label/input association

Required changes:
- use a form system with accessible defaults
- enforce focus states and AA contrast
- verify tab order and grouped semantics

## Target Interaction Model

### Search controls (always visible)
- large natural-language query input
- category selector
- price range
- `More filters` toggle

### More filters (collapsed by default)
- dimensions (width/depth/height)
- advanced controls only
- exact-match toggle switches mode instead of showing exact+range simultaneously

### Results header
- total count (`37 results`)
- sort dropdown
- optional view toggle (`list/grid`)

### Result cards
- image or placeholder
- title + price
- key badges (`56×39×42 cm`, `65 L`, etc.)
- primary actions (`View`, `Add to shortlist`)
- optional explanation disclosure for ranking

## UIkit Adoption Plan (local static assets, not CDN)

Decision:
- use UIkit, but keep files vendored under project static assets (no runtime CDN dependency)

### Asset layout
- `src/ikea_agent/web/static/vendor/uikit/uikit.min.css`
- `src/ikea_agent/web/static/vendor/uikit/uikit.min.js`
- `src/ikea_agent/web/static/vendor/uikit/uikit-icons.min.js`

### Template integration
In `base.html`, load via Django static tags, not CDN URLs.

### Form integration approach
Use one of:
- widget classes set in `forms.py`, or
- `django-widget-tweaks` for template-level class injection

Recommended class patterns:
- inputs: `uk-input`
- selects: `uk-select`
- primary button: `uk-button uk-button-primary`
- layout: `uk-grid-small`, responsive child widths
- advanced filters: accordion/toggle

## Quick wins (first pass)
1. Make query input the visual hero.
2. Collapse advanced filters.
3. Add reset + sort + active filter chips.
4. Convert taxonomy slugs to friendly labels.
5. Redesign result cards with clear price/key facts/CTA.
6. Remove raw semantic score from main row content.

## Acceptance Criteria
- User can submit a basic query with ≤4 controls visible by default.
- User can identify active filters immediately via chips.
- Results list supports pagination + sorting controls.
- Score/debug info is hidden by default and accessible via disclosure.
- No CDN dependency for UI framework assets.
