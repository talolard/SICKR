# In-App Feedback Bundle Capture

## Context

Tal needs a low-friction way to submit debugging feedback directly from the running UI while interacting with chat and 3D rendering. The payload should include user-entered title/comment, multiple images, and optional debugging context (console log, DOM snapshot, UI state), then persist locally in a structured directory under `comments/`.

## Decisions

- Keep UI consistent with existing CopilotKit shell and current component patterns.
- Reuse existing attachment interaction patterns rather than introducing a separate design system.
- Gate backend persistence behind a debug flag.
- Persist each submission in `comments/<slug>--<timestamp>/`.
- Default missing/blank title to `user_comment_from_ui`.
- Apply best-effort redaction for sensitive-looking keys/values in stored debug artifacts.

## Implementation Outline

1. Add backend settings: `feedback_capture_enabled`, `feedback_root_dir`.
2. Add `POST /api/comments` route to FastAPI runtime.
3. Implement bundle writer service for markdown + metadata + optional artifacts.
4. Add Next.js proxy route `ui/src/app/api/comments/route.ts`.
5. Extend UI page with global feedback launcher + modal flow.
6. Support multi-image paste/upload and debug-data toggles in the feedback form.
7. Add backend and frontend tests for route behavior and feedback UX.
8. Update docs and AGENTS guidance for `comments/` usage.

## Acceptance Criteria

- User can open feedback UI, enter title/comment, attach multiple images, and send.
- Server stores bundle in expected folder shape with `comment.md` and artifact files.
- `comment.md` includes a bottom file guide describing generated files.
- Feature is disabled unless debug flag is enabled.
- Tests and docs cover key behavior and operational usage.
