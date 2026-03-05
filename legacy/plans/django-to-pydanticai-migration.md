# Django to PydanticAI Graph Chat Migration

## Scope

Migrate the local web runtime from Django to FastAPI + pydantic-ai web chat.
Keep retrieval, query expansion, reranking, summary generation, and telemetry persistence.

## Subtasks

1. Add FastAPI + graph runtime
- Create typed graph orchestration for parse -> expand -> retrieve -> rerank -> summarize -> refine -> persist -> respond.
- Add FastAPI app with `/healthz`, `/api/chat/run`, `/api/chat/trace/{request_id}`, and `/chat` web UI mounting.
- Add tests for graph and API behavior.

2. Migrate config plane to DuckDB
- Add SQL config tables and seeds for prompt templates and expansion policies.
- Add typed config repository.
- Refactor summary service to use DuckDB config and remove Django ORM dependency.

3. Remove Django surfaces and switch tooling/docs
- Remove Django package and dependency.
- Update Makefile targets and runbooks to use new chat runtime.
- Replace/remove Django-specific tests and ensure quality gates pass.

## Quality gates

- `make format-all`
- `make test`
- `make tidy`
