# Repository Simplification: ikea_agent + Milvus + Legacy Archive

## Summary
Implement the approved simplification plan to center runtime on pydantic-ai + pydantic-graph with Milvus Lite for vector search, keep simple typed inline SQL for DuckDB metadata access, archive older phase/SQL/docs under `legacy/`, and update tooling/docs/tests accordingly.

## Workstreams
1. Package and import migration (`src/ikea_agent` -> `src/ikea_agent`).
2. Retrieval/data access simplification with Milvus Lite backend.
3. PydanticAI provider migration for embeddings client usage.
4. Git LFS data tracking + `data/README.md`.
5. Legacy archive and docs/guidance updates.
6. CopilotKit integration specification.
7. Full quality gate: format, typecheck, tests.

## Constraints
- Keep changes incremental and typed.
- Do not depend on legacy files in active runtime.
- Preserve FastAPI + pydantic-ai + pydantic-graph runtime shape.
