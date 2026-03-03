# Logging Standards

## Intent
Provide consistent logs across ingestion, embedding, and query paths for fast debugging.

## Log Format
- Default format: JSON (`LOG_JSON=true`)
- Human-readable local option: console renderer (`LOG_JSON=false`)

## Required Context
When emitting pipeline logs, include:
- `component`
- `query_id` when handling user queries
- `stage` (`load`, `embed`, `persist`, `rerank`)
- Optional source metadata (file/table/model)

## Log Levels
- `DEBUG`: local diagnosis only
- `INFO`: state transitions and successful milestones
- `WARNING`: recoverable anomalies
- `ERROR`: failed operation requiring intervention

## Implementation Hook
Use `configure_logging()` and `get_logger()` from `src/tal_maria_ikea/logging_config.py`.
