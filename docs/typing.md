# Typing and Static Analysis

## Defaults

- Runtime code uses explicit dataclass-based types for retrieval, agent, and tool boundaries.
- Data access methods return typed domain objects, not preformatted strings.
- New runtime SQL should be inline and local to typed repository functions.

## Tooling

- `pyrefly` is the default type checker in this repository.
- Run:
  - `make typecheck`
  - `make format-all`
  - `make test`

## Legacy Guardrail

Do not import modules from `legacy/` into active runtime code.
