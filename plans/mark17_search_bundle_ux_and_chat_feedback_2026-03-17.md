# Mark 17 Search Bundle UX And Chat Feedback

## Summary

This epic is not a greenfield bundle-panel build. Mark 17 is focused on tightening the existing
search bundle UX: make the bundle card easier to scan, keep long explanations visible, render saved
bundles meaningfully inside chat, and keep request failures visible inline in the transcript.

## Goals

- Verify that bundle item descriptions shown in UI come from hydrated catalog data, not model-authored
  tool arguments.
- Lock the bundle UX in place with focused tests for pricing summaries, full-description affordances,
  clickable chat cards, and selected-bundle feedback.
- Keep runtime failures visible inside the chat stream and improve the inline error presentation enough
  that `make tidy` and the real-UI smoke gate can run cleanly.

## Non-goals

- Reworking the bundle tool contract or adding new search-agent tool fields.
- Replacing the existing bundle card visual language with a different component family.
- Changing the search-agent prompt beyond the audit needed to confirm the description source.

## Approach

1. Audit the search tool contract end to end:
   - prompt inputs
   - backend hydration path
   - UI rendering path
2. Update repo docs so they describe the current in-chat bundle card and inline chat error behavior.
3. Add missing unit coverage for:
   - backend description hydration
   - bundle summary card affordances
   - in-chat bundle tool renderer
   - inline chat error accessibility/callbacks
4. Remove any local lint drift discovered while validating the search-agent page wiring.

## Validation

- Focused UI/unit tests for the touched components
- `make tidy`
- `make ui-test-e2e-real-ui-smoke`
