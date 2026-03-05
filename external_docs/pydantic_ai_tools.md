# PydanticAI Tools (Notes for This Repo)

This is a small, repo-local summary of the PydanticAI tool patterns we rely on when exposing agent tools.

## Core Decorators

- `@agent.tool`: register a tool function whose first argument is `ctx: RunContext[Deps]`.
  Use when the tool needs dependencies (`ctx.deps`) or request-scoped data.
- `@agent.tool_plain`: register a tool function without `RunContext`.
  Use when the tool does not need dependencies.

## Argument Models and JSON Schema

PydanticAI validates tool arguments with Pydantic.

Practical guidance:

- Prefer a single `BaseModel` parameter for tool arguments.
  PydanticAI simplifies the tool JSON schema in this case (the model fields become the tool parameters directly).
- Keep argument models "library-native" where possible.
  If the underlying library already has a config schema, mirror it rather than inventing a parallel domain model.

## Return Types

- Tools can return normal Python values (including Pydantic models) and PydanticAI will serialize them.
- For richer interactions, return `ToolReturn`.
  This supports:
  - `return_value`: a structured value your app can consume
  - `content`: extra content for the model (e.g. images, progress text)
  - `metadata`: extra structured context for UIs or logs

For tools that generate images, `ToolReturn` can include `BinaryContent(data=..., media_type="image/png")`
so the model can "see" the generated artifact without an additional fetch path.

## Validation and Retries

If Pydantic validation fails for tool arguments, PydanticAI automatically prompts the model to retry with corrected inputs.
This is a key reason to keep tool inputs strongly typed and narrowly scoped.
