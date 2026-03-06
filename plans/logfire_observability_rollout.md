# Logfire Observability Rollout

## Goal
Introduce Logfire observability for local agent discovery so runs can be analyzed retroactively and later connected to eval workflows.

## Subtasks
1. `tal_maria_ikea-fwn.1` Bootstrap Logfire in FastAPI + PydanticAI runtime.
2. `tal_maria_ikea-fwn.2` Propagate canonical session identity from UI to agent state.
3. `tal_maria_ikea-fwn.3` Revisit custom observability fields only if native Logfire coverage proves insufficient.
4. `tal_maria_ikea-fwn.4` Add prompt and code version metadata to traces.
5. `tal_maria_ikea-fwn.5` Add eval-ready trace dimensions without eval harness execution.
6. `tal_maria_ikea-fwn.6` Document local Logfire runbook and query patterns.
7. `tal_maria_ikea-fwn.7` Add automated tests for metadata propagation.

## Decisions
- Storage mode: Logfire only.
- Canonical session key: Copilot thread/session id from UI state.
- Payload capture: full payloads in local development.
- Prompt versioning: manual `prompt_version` + optional derived hash.
- Missing token behavior: warn and continue without remote export.
- `fwn.3` policy: native-only for now; custom taxonomy deferred unless gap triggers fire.

## Revisit Triggers For `fwn.3`

- Cannot reliably answer failure queries by `session_id` or thread.
- Cannot compute per-tool reliability/latency needed for iteration decisions.
- Need eval joins that require metadata missing from native traces.
- Repeated manual trace/log correlation indicates missing structured context.
