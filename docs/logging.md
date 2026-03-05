# Logging Standards

- Use module-level loggers (`getLogger(__name__)`).
- Log concise operational facts: query text hash/context, result count, latency.
- Keep log payloads structured and typed where possible.

Current retrieval logs include:
- request id
- result count
- latency
- low-confidence signal
