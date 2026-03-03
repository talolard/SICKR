# 1. Data Audit and Market-Scoped Modeling

## Objective
Prepare a reliable canonical catalog layer in DuckDB that is clean enough for embedding and retrieval.

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
- Define base tables/views:
  - Canonical product table for retrieval.
  - Mapping table for duplicates/families/merged IDs.
  - Optional analytics tables for category and attribute completeness.
- Add a scoped market view for phase-one iteration:
  - Create a view or materialized view that is currently filtered to Germany.
  - Make scope switching explicit by changing one SQL definition, not application code.
- Document a stable product key strategy:
  - Primary key rules when raw IDs collide or are missing.
  - Alias mapping for family/duplicate handling.
- Add SQL scripts for deterministic rebuild of the modeled layer.

## Deliverables
- SQL files for canonical modeling + market-scoped view + mapping tables.
- Updated `docs/data/index.md` with table-level semantics.
- Short data quality report (counts, duplicates, unresolved issues).

## Exit Criteria
- Queryable canonical product table exists, plus a Germany-scoped view/materialized view.
- Duplicate/product-family mapping is explicit and documented.
- Downstream embedding input can be generated with no ambiguous primary key rows.
