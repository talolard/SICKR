# 3. Semantic Retrieval Service over DuckDB

## Objective
Provide a stable query interface that takes user text and returns ranked candidates from pre-indexed vectors.

## Where Work Happens
- `src/ikea_agent/retrieval/` for retrieval service and ranking orchestration.
- `src/ikea_agent/shared/` for shared contracts and settings.
- `sql/` for candidate retrieval/hydration queries.
- `tests/retrieval/` for contract and behavior tests.

## Tasks
- Define retrieval contract:
  - Input: query text, optional filters, limit.
  - Output: ranked product results with score and minimal explanation metadata.
- Implement query embedding path:
  - Use Gemini embedding settings aligned with index strategy.
  - Log query IDs for traceability.
- Implement candidate retrieval:
  - Vector similarity search against stored embeddings.
  - Join back to canonical product table and mapping tables.
- Add retrieval safeguards:
  - Limit controls.
  - Empty/low-confidence response handling.
  - Basic latency instrumentation.

## Deliverables
- Retrieval module callable by web app.
- SQL for vector/candidate lookup and product hydration.
- Documented response shape and error handling behavior.

## Exit Criteria
- Retrieval contract is stable and tested with representative queries.
- Results resolve to canonical Germany product rows.
- Logs support query-to-result debugging.
