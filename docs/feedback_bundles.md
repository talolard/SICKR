# Feedback Bundles

## Purpose

In-app feedback bundles capture user comments and debugging context while using the IKEA UI (including 3D renderer workflows). This reduces back-and-forth for reproduction by keeping screenshots and runtime context together.

## Enablement

Set these environment variables in `.env`:

- `FEEDBACK_CAPTURE_ENABLED=true`
- `FEEDBACK_ROOT_DIR=comments` (or a custom local path)

When disabled, `POST /api/comments` returns `503`.

## Directory Layout

Each submission is written to:

- `comments/<slug>--<YYYYMMDDTHHMMSSZ>/`

Where:

- `<slug>` derives from report title (`the_problem_with_svg` style)
- blank title falls back to `user_comment_from_ui`
- UTC timestamp suffix guarantees uniqueness

## Bundle Files

- `comment.md`: user-facing summary of title/comment plus metadata and file guide
- `metadata.json`: machine-readable metadata and artifact paths
- `images/*`: pasted/uploaded screenshots
- `console_log.ndjson`: captured browser console/error records (if enabled)
- `dom_snapshot.html`: DOM snapshot at submission time (if enabled)
- `ui_state.json`: captured UI state snapshot (if enabled)

## Redaction

Structured debug artifacts (`console_log.ndjson`, `ui_state.json`) are stored with best-effort redaction of sensitive-looking keys/values, including patterns such as `password`, `token`, `secret`, `api_key`, and `authorization`.

## Notes

- Feedback route is intended for local/debug use in this project.
- Payload fidelity is intentionally high; use toggles in the feedback dialog when you want smaller bundles.
