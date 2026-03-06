# Logfire Observability Rollout

## Goal
Introduce Logfire observability for local agent discovery so runs can be analyzed retroactively and later connected to eval workflows.

## Subtasks
1. `tal_maria_ikea-fwn.1` Bootstrap Logfire in FastAPI + PydanticAI runtime.
2. `tal_maria_ikea-fwn.2` Propagate canonical session identity from UI to agent state.
3. `tal_maria_ikea-fwn.3` Instrument agent and tool lifecycle events with correlation metadata.
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
