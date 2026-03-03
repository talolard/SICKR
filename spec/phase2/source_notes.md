Phase two: feedback integration notes.

## Existing feedback themes

- **store raw and intermediate data in parquet** This way we will have our structured data and vectors in an easily accessible format for analysis and iteration without needing to re-run embedding jobs. We can use DuckDB to query and sample from the parquet files as we iterate on embedding strategies.
- **Precompute Embeddings** Run embeddings on all the texts once at full dimension. Store them in Parquet. Do not check it in, add a TODO for Git LFS.
- **Have duckdb load the vector data directly from Parquet** instead of embedding on the fly in Python. ensure the parquet data is partitioned by country so we can be efficient in loading only the relevant subset for Germany.  
- 
- **Do not inject missing values into embedding text** Omit empty/missing attributes (`badge=none`, `dimensions=na`, etc.) instead of serializing placeholders.
- **Add country and rating signals into embedding text** Add `country`, `rating`, `rating_count` when present.

## New request: multi-country description rollup by product id

### Clarified ask

1. Build a derived table **before Germany filtering** from `app.products_raw`.
2. Key it by non-country product identity (`product_id`, e.g. `10056770`).
3. Group descriptions by `(product_id, description_text)` so repeated text across countries appears once.
4. For each grouped description, collect the distinct countries that share that text.
5. Feed this rolled-up data into embedding text so descriptions become market-aware:
`description (countries: Germany)` for one country and
`description (countries: Germany, France, Italy)` for multi-country.

### Proposed derived table

Table name proposal: `app.product_description_country_rollup`

Columns:

- `product_id BIGINT NOT NULL`
- `description_text VARCHAR NOT NULL`
- `countries VARCHAR[] NOT NULL` (distinct, sorted)
- `country_count INTEGER NOT NULL`
- `source_row_count INTEGER NOT NULL`
- `description_hash VARCHAR NOT NULL` (optional deterministic id)
- `created_at TIMESTAMP DEFAULT now()`
- `PRIMARY KEY (product_id, description_hash)` or `(product_id, description_text)`

Foreign key intent:

- `product_id` links to canonical records through `products_canonical.product_id` (Germany currently, multi-market later).

### SQL shape for rollup

Core aggregation sketch:

```sql
SELECT
  product_id,
  trim(product_description) AS description_text,
  list_sort(list_distinct(list(country))) AS countries,
  list_count(list_sort(list_distinct(list(country)))) AS country_count,
  COUNT(*) AS source_row_count
FROM app.products_raw
WHERE product_id IS NOT NULL
  AND product_description IS NOT NULL
  AND length(trim(product_description)) > 0
GROUP BY product_id, trim(product_description);
```

### Embedding text integration idea

For each Germany canonical row:

1. Join on `product_id`.
2. Build one or more lines from rollup rows, for example:
`description_by_market: [Germany, France] <text>`
3. Keep deterministic ordering:

- higher `country_count` first
- then lexical country list
- then stable hash/text

4. If only one country exists, keep singular semantics:
`description_country: Germany`.
2. If many descriptions exist for one product id, cap to top `N` lines to control token size.

## Ambiguities to resolve before implementation

- Should description dedupe use exact match only, or normalized text (whitespace/case/punctuation)?
- If a product has many distinct descriptions, what max `N` should be embedded?
- Should country values in embedding text use full names (`Germany`) or compact codes (`DE`)?
- Should we include only lines containing `Germany`, or all markets for that `product_id`?
- Do we include `source_row_count`/confidence metadata in the text block?
- For rows with missing `product_id`, do we skip entirely (recommended) or create fallback grouping?

## Planned implementation sequence

1. Add new SQL model file to create/populate rollup table from raw source.
2. Add data quality/profile query:

- rollup rows by product,
- distribution of `country_count`,
- products with >1 distinct description.

3. Extend embedding-input SQL view (`v2_metadata_first`) to append market-aware description block.
2. Add tests for:

- one-country description block formatting,
- multi-country block formatting,
- deterministic ordering and dedupe behavior.

5. Reindex subset and compare retrieval behavior + token length impact.
