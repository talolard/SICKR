# Logging Standards

## Baseline Policy

- Use module-level loggers (`getLogger(__name__)`).
- Log concise operational facts: query text hash/context, result count, latency.
- Keep log payloads structured and typed where possible.
- Prefer native Logfire instrumentation first:
  - `logfire.instrument_pydantic_ai()`
  - `logfire.instrument_fastapi(app)`

## Native Coverage (Current)

With native PydanticAI + FastAPI instrumentation enabled, we rely on Logfire to capture:

- agent/model run spans
- tool call spans, including args/results where integration exposes them
- request/response tracing around FastAPI runtime paths

## Custom Observability Rule

- Do **not** add a custom event taxonomy by default.
- Add custom events/fields only when a concrete query or debugging use case cannot be answered from native traces.
- If a gap is found, document it and open a beads task first.

## Gap Triggers (When To Revisit)

Revisit custom instrumentation only if one or more are true:

- We cannot reliably query failures by `session_id` / thread.
- We cannot compute per-tool reliability/latency needed for decisions.
- Future eval joins need fields not available in native trace context.
- We repeatedly require manual cross-correlation between logs and spans.

## Enforcement (Current)

- Discovery phase enforcement is warning-based, not hard-fail CI.
- Missing metadata should produce a warning + follow-up bead.
- Hard CI contracts for observability schema are deferred until a clear need emerges.

Current retrieval logs include:
- request id
- result count
- latency
- low-confidence signal
