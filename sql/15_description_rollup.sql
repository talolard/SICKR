-- Build market-aware description rollup by product identity before country filtering.

DELETE FROM app.product_description_country_rollup;

INSERT INTO app.product_description_country_rollup (
    product_id,
    description_text,
    countries,
    country_count,
    source_row_count,
    description_hash,
    created_at
)
SELECT
    product_id,
    trim(product_description) AS description_text,
    list_sort(list_distinct(list(country))) AS countries,
    list_count(list_sort(list_distinct(list(country)))) AS country_count,
    COUNT(*) AS source_row_count,
    md5(trim(product_description)) AS description_hash,
    now()
FROM app.products_raw
WHERE product_id IS NOT NULL
  AND product_description IS NOT NULL
  AND length(trim(product_description)) > 0
GROUP BY product_id, trim(product_description);
