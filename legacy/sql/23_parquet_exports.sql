-- Export reusable local parquet artifacts for iteration.
-- TODO: If these artifacts should be versioned, add Git LFS policy before committing them.

COPY (
    SELECT * FROM app.products_raw
) TO 'data/parquet/products_raw' (FORMAT parquet, PARTITION_BY (country), OVERWRITE_OR_IGNORE 1);

COPY (
    SELECT * FROM app.products_canonical
) TO 'data/parquet/products_canonical' (FORMAT parquet, PARTITION_BY (country), OVERWRITE_OR_IGNORE 1);

COPY (
    SELECT
        canonical_product_key,
        embedding_model,
        run_id,
        embedding_vector,
        embedded_text,
        embedded_at
    FROM app.product_embeddings
) TO 'data/parquet/product_embeddings' (FORMAT parquet, OVERWRITE_OR_IGNORE 1);

COPY (
    SELECT
        product_id,
        description_text,
        countries,
        country_count,
        source_row_count,
        description_hash,
        created_at
    FROM app.product_description_country_rollup
) TO 'data/parquet/product_description_country_rollup' (FORMAT parquet, OVERWRITE_OR_IGNORE 1);
