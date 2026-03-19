# Design System: The Editorial Assistant

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Digital Curator."** 

We are moving away from the cold, clinical efficiency of traditional tech and toward the tactile, warm experience of a high-end interior design magazine. This system is built on the tension between **Editorial Authority** (the expert) and **Domestic Warmth** (the friend). 

To break the "template" look, we reject rigid, symmetrical grids in favor of intentional asymmetry. Layouts should feel "composed" rather than "calculated." We achieve this through overlapping elements, generous use of whitespace (negative space as a luxury), and a dramatic scale shift between our serif display type and sans-serif functional UI.

## 2. Colors & Surface Philosophy
The palette is a sophisticated study in warm neutrals, anchored by deep forest greens and spiced with terracotta.

### The "No-Line" Rule
**Explicit Instruction:** Use of 1px solid borders for sectioning or containment is strictly prohibited. Boundaries must be defined solely through background color shifts. 
- A card should not have a border; it should sit as a `surface-container-lowest` block on a `surface-container-low` background. 
- If a visual break is needed, use a transition from `surface` to `surface-variant`.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like fine linen paper stacked on an oak table.
- **Base Layer:** `surface` (#fff8f2) – Use for the overall canvas.
- **Sectional Layer:** `surface-container-low` (#fef2e0) – Use for large secondary areas (e.g., a sidebar or a "Suggested Rooms" tray).
- **Interactive Layer:** `surface-container-lowest` (#ffffff) – Reserved for the most important interactive cards to make them "pop" against the warmer background.

### The "Glass & Gradient" Rule
To add "soul," use Glassmorphism for floating elements (like a navigation bar or an AI chat bubble). Apply a semi-transparent `surface` color with a 12px-20px `backdrop-blur`. 
- **Signature CTA Texture:** For primary buttons or Hero accents, use a subtle linear gradient from `primary` (#18241b) to `primary-container` (#2d3930). This prevents the deep green from looking flat and "digital."

## 3. Typography
Our typography is a conversation between two distinct personalities.

- **The Voice (Display & Headline):** `notoSerif`. This is our "Editorial" voice. Use `display-lg` for hero statements and `headline-md` for section titles. The serif nature conveys expertise and a timeless aesthetic.
- **The Utility (Title, Body, Label):** `plusJakartaSans`. This is our "Friendly" voice. It is clean, legible, and modern. It ensures the AI feels tech-forward and accessible.

**Design Note:** Always pair a large `headline-lg` serif with a much smaller `body-md` sans-serif. This extreme contrast in scale is what creates the "premium magazine" feel.

## 4. Elevation & Depth
We convey hierarchy through **Tonal Layering** rather than traditional drop shadows.

- **The Layering Principle:** Depth is achieved by stacking tiers. Place a `surface-container-highest` element on top of a `surface` background to create a "lift" that feels integrated into the room, not floating above it.
- **Ambient Shadows:** If an element must float (e.g., a modal), use an ultra-diffused shadow: `box-shadow: 0 20px 40px rgba(32, 27, 16, 0.06)`. Note the use of the `on-surface` color (#201b10) for the shadow tint—never use pure black.
- **The "Ghost Border" Fallback:** If accessibility requires a stroke (e.g., in high-contrast modes), use `outline-variant` at 15% opacity. It should be felt, not seen.

## 5. Components

### Buttons
- **Primary:** `primary` background with `on-primary` text. Use `xl` (1.5rem) rounding. No border. Apply the signature subtle gradient.
- **Secondary:** `secondary-container` background. This provides the "terracotta" warmth against the green primary actions.
- **Tertiary:** Text-only using `primary` color, bolded, with a 2px underline in `surface-tint` spaced 4px below the baseline.

### Input Fields
- Avoid the "box" look. Use `surface-container-high` as a solid background with `xl` rounding. 
- **Focus State:** Do not use a blue glow. Shift the background to `surface-container-highest` and add a 1px `primary` "Ghost Border" at 20% opacity.

### Cards & Lists
- **Rule:** Forbid divider lines. 
- Use vertical white space (Scale `6` or `8`) to separate list items. 
- For cards, use `surface-container-lowest` for the card body and `surface-dim` for a "footer" or "metadata" area within the card to create internal hierarchy without lines.

### Suggestion Chips
- Use `tertiary-fixed` with `full` rounding. These should feel like small smooth stones. They provide a tactile, "pick-up-able" quality to the AI's suggestions.

### The "Curator" Moodboard (Custom Component)
- An asymmetrical grid of images with varying border-radii (some `lg`, some `xl`). Overlap a `surface-container-lowest` text label over the corner of the image to create a layered, "collage" effect.

## 6. Do's and Don'ts

### Do
- **Do** use `24` (8.5rem) spacing for top-level section margins. High-end design needs room to breathe.
- **Do** use `notoSerif` for numbers in a list to make them feel like architectural annotations.
- **Do** use the `secondary` terracotta sparingly as an "accent of warmth"—like a throw pillow in a dark room.

### Don't
- **Don't** use 100% black (#000000) for text. Use `on-surface` (#201b10) for a softer, more organic reading experience.
- **Don't** use sharp 90-degree corners. Everything must feel "softened" and domestic.
- **Don't** use standard "Loading" spinners. Use a soft, pulsing opacity transition on a `primary-container` shape to feel more like a "breath."