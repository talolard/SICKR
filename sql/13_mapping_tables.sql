-- Additional mapping and data quality analytics tables.

CREATE TABLE IF NOT EXISTS app.product_quality_summary AS
SELECT
    country,
    COUNT(*) AS row_count,
    COUNT(*) FILTER (WHERE product_id IS NULL) AS missing_product_id_count,
    COUNT(*) FILTER (WHERE product_description IS NULL OR product_description = '') AS missing_description_count,
    COUNT(*) FILTER (WHERE price IS NULL) AS missing_price_count
FROM app.products_raw
GROUP BY country;
