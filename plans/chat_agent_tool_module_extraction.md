# Chat Agent Tool Module Extraction

## Goal
Reduce complexity in `src/ikea_agent/chat/agent.py` by moving inline tool definitions from `build_chat_agent` into focused modules under `src/ikea_agent/chat/tools/`.

## Scope
- Keep tool names and signatures unchanged.
- Group tools by domain:
  - search/state context tools
  - floor-plan tools
  - image analysis tools
- Keep persistence and telemetry behavior equivalent.

## Implementation Steps
1. Create a shared helper module for telemetry context, repositories, and snapshot payload helpers.
2. Add registration modules that define tools and register them on the passed agent.
3. Simplify `build_chat_agent` to model + agent construction plus tool registration calls.
4. Run tests and `make tidy`.

## Risks
- Tool registration decorators moved into modules could accidentally change tool names or signatures.
- Imports can regress if type references become circular.

## Validation
- Run focused chat tests and full `make tidy`.
- Verify tool contract tests still pass.
