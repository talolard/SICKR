# 1. Data Audit and Germany-Focused Modeling

## Objective
Prepare a reliable Germany-focused catalog layer in DuckDB that is clean enough for embedding and retrieval.

## Where Work Happens
- `sql/` for all schema/modeling/profiling queries.
- `scripts/` for reproducible DB build/profile commands.
- `docs/data/` for schema and column semantics.

## Why First
The later pipeline quality is bounded by product normalization and deduplication quality.

## Tasks
- Profile the incoming IKEA catalog data in DuckDB:
  - Identify country/market columns and Germany filter logic.
  - Quantify nulls, duplicate product IDs, and likely product-family collisions.
- Define Germany-first base tables/views:
  - Canonical product table for retrieval.
  - Mapping table for duplicates/families/merged IDs.
  - Optional analytics tables for category and attribute completeness.
- Document a stable product key strategy:
  - Primary key rules when raw IDs collide or are missing.
  - Alias mapping for family/duplicate handling.
- Add SQL scripts for deterministic rebuild of the modeled layer.

## Deliverables
- SQL files for Germany filtering + normalization + mapping tables.
- Updated `docs/data/index.md` with table-level semantics.
- Short data quality report (counts, duplicates, unresolved issues).

## Exit Criteria
- Queryable Germany-only canonical product table exists.
- Duplicate/product-family mapping is explicit and documented.
- Downstream embedding input can be generated with no ambiguous primary key rows.

