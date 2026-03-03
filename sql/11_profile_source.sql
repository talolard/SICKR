-- Data profile queries for source quality and Germany scope.

-- Country distribution.
SELECT country, COUNT(*) AS row_count
FROM app.products_raw
GROUP BY country
ORDER BY row_count DESC;

-- Germany row count and key completeness.
SELECT
    COUNT(*) AS germany_rows,
    COUNT(*) FILTER (WHERE product_id IS NULL) AS missing_product_id,
    COUNT(*) FILTER (WHERE unique_id IS NULL) AS missing_unique_id,
    COUNT(*) FILTER (WHERE product_name IS NULL OR product_name = '') AS missing_name
FROM app.products_raw
WHERE country = 'Germany';

-- Duplicate product_id frequency in Germany.
SELECT product_id, COUNT(*) AS dup_count
FROM app.products_raw
WHERE country = 'Germany' AND product_id IS NOT NULL
GROUP BY product_id
HAVING COUNT(*) > 1
ORDER BY dup_count DESC, product_id;

-- Null rates for key retrieval fields.
SELECT
    AVG(CASE WHEN product_description IS NULL OR product_description = '' THEN 1 ELSE 0 END) AS null_desc_rate,
    AVG(CASE WHEN main_category IS NULL OR main_category = '' THEN 1 ELSE 0 END) AS null_main_category_rate,
    AVG(CASE WHEN product_measurements IS NULL OR product_measurements = '' THEN 1 ELSE 0 END) AS null_measurements_rate,
    AVG(CASE WHEN price IS NULL THEN 1 ELSE 0 END) AS null_price_rate
FROM app.products_raw
WHERE country = 'Germany';

-- Germany dimensions format distribution.
SELECT
    CASE
        WHEN product_measurements IS NULL OR trim(lower(product_measurements)) IN ('', 'none')
            THEN 'missing'
        WHEN regexp_matches(trim(lower(product_measurements)), '^\\d+(?:[.,]\\d+)?\\s*cm$')
            THEN 'cm_single'
        WHEN regexp_matches(trim(lower(product_measurements)), '^\\d+(?:[.,]\\d+)?\\s*x\\s*\\d+(?:[.,]\\d+)?\\s*cm$')
            THEN 'cm_double'
        WHEN regexp_matches(trim(lower(product_measurements)), '^\\d+(?:[.,]\\d+)?\\s*x\\s*\\d+(?:[.,]\\d+)?\\s*x\\s*\\d+(?:[.,]\\d+)?\\s*cm$')
            THEN 'cm_triple'
        WHEN strpos(trim(lower(product_measurements)), '(') > 0 AND regexp_matches(trim(lower(product_measurements)), 'cm')
            THEN 'cm_with_parenthetical'
        WHEN regexp_matches(trim(lower(product_measurements)), '/') AND regexp_matches(trim(lower(product_measurements)), 'cm')
            THEN 'cm_with_alternatives'
        WHEN regexp_matches(trim(lower(product_measurements)), 'm²') AND regexp_matches(trim(lower(product_measurements)), 'cm')
            THEN 'area_with_height'
        WHEN regexp_matches(trim(lower(product_measurements)), 'cm')
            THEN 'cm_other'
        ELSE 'non_cm_or_unknown'
    END AS dimensions_type,
    COUNT(*) AS row_count
FROM app.products_raw
WHERE country = 'Germany'
GROUP BY dimensions_type
ORDER BY row_count DESC;
