# Data Patterns (Phase 1)

## Germany Scope Snapshot
- Source table: `app.products_raw`
- Germany filter: `country = 'Germany'`
- Current observed Germany row count from source profiling: `~10k` rows

## Stable Patterns
- `product_id` repeats across markets; treat `(product_id + market)` as scoped identity.
- `unique_id` includes market suffix and is useful for alias mapping.
- `currency` is EUR for Germany rows; price filters use parsed `price_eur`.

## Known Irregularities
- `product_measurements` format is not fully uniform; parser extracts first 3 numeric tokens.
- Some rows have `none` strings for rating fields and optional text attributes.
- Category text can drift by locale in non-Germany rows; retrieval is built over Germany-scoped canonical table.
- Distinct descriptions per `product_id` are frequently high due localization and size variants.
- `product_name` is often only a family/series label (for example `FEJKA`), so runtime
  display should prefer the durable `products_canonical.display_title` enrichment when
  present instead of deriving titles in the UI.

## Dimensions Format Families
`products_canonical.dimensions_type` now classifies dimension strings into:
- `missing`
- `cm_single`
- `cm_double`
- `cm_triple`
- `cm_with_parenthetical` (metric + imperial in parentheses)
- `cm_with_alternatives` (slash alternatives, e.g. `140x200/80x80 cm`)
- `area_with_height` (area-like + thickness pattern, e.g. `1 m²x2.0 cm`)
- `cm_other`
- `non_cm_or_unknown`

Parsing policy:
- Use normalized metric segment before `(` when present.
- Extract first 3 numeric tokens as width/depth/height.
- Keep `dimensions_type` to support future format-specific handling improvements.

## Useful Queries
```sql
-- Country distribution
SELECT country, COUNT(*) FROM app.products_raw GROUP BY country ORDER BY 2 DESC;

-- Germany duplicates by product_id
SELECT product_id, COUNT(*)
FROM app.products_raw
WHERE country = 'Germany'
GROUP BY product_id
HAVING COUNT(*) > 1
ORDER BY 2 DESC;

-- Canonical coverage
SELECT COUNT(*) AS canonical_rows FROM app.products_canonical;

-- Dimensions type distribution
SELECT dimensions_type, COUNT(*) AS n
FROM app.products_canonical
GROUP BY dimensions_type
ORDER BY n DESC;

-- Distinct descriptions per product_id (before Germany filtering)
WITH rollup AS (
  SELECT
    product_id,
    trim(product_description) AS description_text
  FROM app.products_raw
  WHERE product_id IS NOT NULL
    AND product_description IS NOT NULL
    AND length(trim(product_description)) > 0
  GROUP BY product_id, trim(product_description)
),
per_product AS (
  SELECT product_id, COUNT(*) AS distinct_description_count
  FROM rollup
  GROUP BY product_id
)
SELECT
  COUNT(*) AS products_with_descriptions,
  SUM(CASE WHEN distinct_description_count > 5 THEN 1 ELSE 0 END) AS gt_5,
  SUM(CASE WHEN distinct_description_count > 10 THEN 1 ELSE 0 END) AS gt_10,
  SUM(CASE WHEN distinct_description_count > 15 THEN 1 ELSE 0 END) AS gt_15,
  MAX(distinct_description_count) AS max_count
FROM per_product;
```

Observed locally on 2026-03-03:
- `products_with_descriptions=34932`
- `gt_5=10982`
- `gt_10=6077`
- `gt_15=830`
- `max_count=25`

## Query That Should Be Avoided in Early Iteration
```sql
-- Avoid full payload scans with wide SELECT * in early profiling.
SELECT * FROM app.products_raw;
```
