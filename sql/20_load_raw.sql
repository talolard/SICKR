-- Load CSV records into raw table.

DELETE FROM app.products_raw;

INSERT INTO app.products_raw (
    unique_id,
    product_id,
    product_name,
    product_type,
    product_measurements,
    product_description,
    main_category,
    sub_category,
    product_rating,
    product_rating_count,
    badge,
    online_sellable,
    url,
    price,
    currency,
    discount,
    sale_tag,
    country
)
SELECT
    unique_id,
    product_id,
    product_name,
    product_type,
    product_measurements,
    product_description,
    main_category,
    sub_category,
    product_rating,
    product_rating_count,
    badge,
    online_sellable,
    url,
    price,
    currency,
    discount,
    sale_tag,
    country
FROM read_csv_auto(getenv('CSV_PATH'));
