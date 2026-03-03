-- Load CSV into raw table, then normalize into products table.

INSERT INTO app.products_raw (source_row_id, payload)
SELECT
    row_number() OVER () AS source_row_id,
    to_json(t)
FROM read_csv_auto(getenv('CSV_PATH')) AS t;

INSERT OR REPLACE INTO app.products (
    product_id,
    product_name,
    category,
    description,
    dimensions_text,
    price_text,
    currency,
    updated_at
)
SELECT
    coalesce(cast(json_extract_string(payload, '$.item_no') AS VARCHAR),
             cast(source_row_id AS VARCHAR)) AS product_id,
    coalesce(json_extract_string(payload, '$.name'), 'UNKNOWN') AS product_name,
    json_extract_string(payload, '$.category') AS category,
    json_extract_string(payload, '$.short_description') AS description,
    json_extract_string(payload, '$.measurements') AS dimensions_text,
    json_extract_string(payload, '$.price') AS price_text,
    json_extract_string(payload, '$.currency') AS currency,
    now() AS updated_at
FROM app.products_raw;
